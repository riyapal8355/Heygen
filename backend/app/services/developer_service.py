"""Developer service orchestrating API keys, Webhook registrations, and security verification."""

import hashlib
import hmac
import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AppException,
    AuthenticationException,
    ForbiddenException,
    NotFoundException,
)
from app.core.logging import get_logger
from app.core.redis import check_rate_limit
from app.core.ssrf import validate_destination_url
from app.models.developer import ApiKey, Webhook, WebhookDelivery
from app.models.workspace import Workspace
from app.repositories.developer import ApiKeyRepository, WebhookDeliveryRepository, WebhookRepository
from app.repositories.workspace import WorkspaceRepository
from app.schemas.developer import ApiKeyCreateRequest, WebhookCreateRequest, WebhookUpdateRequest

logger = get_logger(__name__)


class DeveloperService:
    """Service handling API key lifecycle, webhook endpoints, and delivery auditing."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.api_key_repo = ApiKeyRepository(db)
        self.webhook_repo = WebhookRepository(db)
        self.delivery_repo = WebhookDeliveryRepository(db)
        self.workspace_repo = WorkspaceRepository(db)

    # =========================================================================
    # API Key Operations
    # =========================================================================

    async def create_api_key(
        self,
        workspace_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        request: ApiKeyCreateRequest,
    ) -> Tuple[ApiKey, str]:
        """Generate and persist a new workspace developer API key.

        Returns: (api_key_record, plaintext_secret_key)
        """
        # Rate-limiting: max 10 key creations per 10 minutes per workspace
        rate_key = f"rate:api_key:create:{workspace_id}"
        allowed = await check_rate_limit(rate_key, max_requests=10, window_seconds=600)
        if not allowed:
            raise AppException(
                status_code=429,
                code="RATE_LIMIT_EXCEEDED",
                message="Rate limit exceeded for API key creation. Please try again later.",
            )

        env_prefix = "live" if request.environment == "production" else "test"
        public_id = secrets.token_hex(4)  # 8 hex chars
        prefix = f"hz_{env_prefix}_{public_id}"

        # Generate 32-byte cryptographically secure random secret
        secret = secrets.token_urlsafe(32)
        plaintext_key = f"{prefix}_{secret}"

        # Compute SHA-256 hash of secret for constant-time lookup & verification
        secret_hash = hashlib.sha256(secret.encode("utf-8")).hexdigest()

        expires_at: Optional[datetime] = None
        if request.expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=request.expires_in_days)

        api_key = ApiKey(
            workspace_id=workspace_id,
            created_by=user_id,
            name=request.name.strip(),
            prefix=prefix,
            key_hash=secret_hash,
            environment=request.environment,
            permissions=request.permissions,
            status="active",
            expires_at=expires_at,
        )

        created_key = await self.api_key_repo.create(api_key)
        await self.db.commit()

        logger.info(
            "Created API key prefix=%s for workspace_id=%s environment=%s",
            prefix,
            workspace_id,
            request.environment,
        )
        return created_key, plaintext_key

    async def list_api_keys(
        self,
        workspace_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[ApiKey], int]:
        """List API keys for a given workspace."""
        return await self.api_key_repo.list_by_workspace(
            workspace_id=workspace_id,
            limit=limit,
            offset=offset,
        )

    async def get_api_key(
        self,
        workspace_id: uuid.UUID,
        key_id: uuid.UUID,
    ) -> ApiKey:
        """Fetch API key metadata verifying workspace boundary."""
        key = await self.api_key_repo.get_by_id(key_id, workspace_id=workspace_id)
        if not key:
            raise NotFoundException(
                code="API_KEY_NOT_FOUND",
                message="API key not found.",
            )
        return key

    async def revoke_api_key(
        self,
        workspace_id: uuid.UUID,
        key_id: uuid.UUID,
    ) -> ApiKey:
        """Revoke an active API key."""
        key = await self.get_api_key(workspace_id=workspace_id, key_id=key_id)
        if key.status == "revoked":
            return key

        revoked = await self.api_key_repo.revoke(key)
        await self.db.commit()
        logger.info("Revoked API key id=%s prefix=%s in workspace=%s", key.id, key.prefix, workspace_id)
        return revoked

    async def authenticate_api_key(self, raw_key: str) -> Tuple[ApiKey, Workspace]:
        """Authenticate caller using raw API key string.

        Performs:
        1. Format extraction: hz_<env>_<public_id>_<secret>
        2. Prefix query
        3. Constant-time SHA-256 hash comparison
        4. Status & expiration check
        5. Workspace resolution
        6. Asynchronous last_used_at update

        Raises AuthenticationException on ANY failure (without leaking specifics).
        """
        if not raw_key or not isinstance(raw_key, str):
            raise AuthenticationException(
                code="AUTH_INVALID_API_KEY",
                message="Invalid API key format.",
            )

        parts = raw_key.strip().split("_")
        # Expected parts: ['hz', 'live'|'test', '<public_id>', '<secret>']
        if len(parts) < 4 or parts[0] != "hz":
            raise AuthenticationException(
                code="AUTH_INVALID_API_KEY",
                message="Invalid API key format.",
            )

        prefix = f"{parts[0]}_{parts[1]}_{parts[2]}"
        secret = "_".join(parts[3:])

        key = await self.api_key_repo.get_by_prefix(prefix)
        if not key:
            # Constant-time dummy comparison to prevent timing side-channels
            hmac.compare_digest(
                "0" * 64,
                hashlib.sha256(secret.encode("utf-8")).hexdigest(),
            )
            raise AuthenticationException(
                code="AUTH_INVALID_API_KEY",
                message="Invalid API key.",
            )

        # Constant-time comparison of secret hash
        candidate_hash = hashlib.sha256(secret.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(key.key_hash, candidate_hash):
            raise AuthenticationException(
                code="AUTH_INVALID_API_KEY",
                message="Invalid API key.",
            )

        # Check status and expiration
        if not key.is_active:
            raise AuthenticationException(
                code="AUTH_INVALID_API_KEY",
                message="API key is expired or revoked.",
            )

        # Resolve associated workspace
        workspace = await self.workspace_repo.get_by_id(key.workspace_id)
        if not workspace or workspace.status != "active":
            raise AuthenticationException(
                code="AUTH_INVALID_API_KEY",
                message="Workspace associated with API key is inactive.",
            )

        # Asynchronously update last_used_at without blocking auth critical path
        try:
            await self.api_key_repo.update_last_used(key.id)
        except Exception as exc:
            logger.warning("Failed to update last_used_at for key %s: %s", key.id, exc)

        return key, workspace

    # =========================================================================
    # Webhook Operations
    # =========================================================================

    async def create_webhook(
        self,
        workspace_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        request: WebhookCreateRequest,
    ) -> Tuple[Webhook, str]:
        """Register a new webhook destination with SSRF validation.

        Returns: (webhook_record, signing_secret)
        """
        # Rate-limiting: max 10 webhook registrations per 10 minutes per workspace
        rate_key = f"rate:webhook:create:{workspace_id}"
        allowed = await check_rate_limit(rate_key, max_requests=10, window_seconds=600)
        if not allowed:
            raise AppException(
                status_code=429,
                code="RATE_LIMIT_EXCEEDED",
                message="Rate limit exceeded for webhook registration. Please try again later.",
            )

        # Validate URL against SSRF boundary
        safe_url = validate_destination_url(request.url)

        # Generate cryptographic signing secret: whsec_<random>
        secret = f"whsec_{secrets.token_urlsafe(32)}"

        webhook = Webhook(
            workspace_id=workspace_id,
            created_by=user_id,
            url=safe_url,
            secret=secret,
            events=request.events or ["job.succeeded", "job.failed"],
            status="active",
            description=request.description.strip() if request.description else None,
        )

        created_webhook = await self.webhook_repo.create(webhook)
        await self.db.commit()

        logger.info(
            "Registered webhook id=%s url=%s for workspace=%s",
            created_webhook.id,
            safe_url,
            workspace_id,
        )
        return created_webhook, secret

    async def list_webhooks(
        self,
        workspace_id: uuid.UUID,
        status: Optional[str] = None,
    ) -> List[Webhook]:
        """List registered webhooks for a workspace."""
        return await self.webhook_repo.list_by_workspace(workspace_id=workspace_id, status=status)

    async def get_webhook(
        self,
        workspace_id: uuid.UUID,
        webhook_id: uuid.UUID,
    ) -> Webhook:
        """Fetch webhook metadata verifying workspace boundary."""
        webhook = await self.webhook_repo.get_by_id(webhook_id, workspace_id=workspace_id)
        if not webhook:
            raise NotFoundException(
                code="WEBHOOK_NOT_FOUND",
                message="Webhook endpoint not found.",
            )
        return webhook

    async def update_webhook(
        self,
        workspace_id: uuid.UUID,
        webhook_id: uuid.UUID,
        request: WebhookUpdateRequest,
    ) -> Webhook:
        """Update an existing webhook configuration."""
        webhook = await self.get_webhook(workspace_id=workspace_id, webhook_id=webhook_id)

        if request.url is not None:
            webhook.url = validate_destination_url(request.url)
        if request.events is not None:
            webhook.events = request.events
        if request.status is not None:
            webhook.status = request.status
        if request.description is not None:
            webhook.description = request.description.strip()

        updated = await self.webhook_repo.update(webhook)
        await self.db.commit()
        return updated

    async def delete_webhook(
        self,
        workspace_id: uuid.UUID,
        webhook_id: uuid.UUID,
    ) -> None:
        """Revoke / soft-delete a webhook."""
        webhook = await self.get_webhook(workspace_id=workspace_id, webhook_id=webhook_id)
        await self.webhook_repo.delete(webhook)
        await self.db.commit()
        logger.info("Deleted webhook id=%s in workspace=%s", webhook_id, workspace_id)

    async def list_deliveries(
        self,
        workspace_id: uuid.UUID,
        webhook_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[WebhookDelivery], int]:
        """List delivery audit history for a webhook."""
        # Ensure webhook belongs to workspace
        await self.get_webhook(workspace_id=workspace_id, webhook_id=webhook_id)
        return await self.delivery_repo.list_by_webhook(
            webhook_id=webhook_id,
            limit=limit,
            offset=offset,
        )

    async def dispatch_event_webhooks(
        self,
        workspace_id: uuid.UUID,
        event_id: str,
        event_type: str,
        payload_data: dict,
    ) -> int:
        """Dispatch an event asynchronously to all active subscribed webhooks in the workspace.

        Enqueues a Celery task for each matching webhook.
        Returns: Count of dispatched webhook delivery tasks.
        """
        webhooks = await self.webhook_repo.list_by_workspace(workspace_id=workspace_id, status="active")
        matching_webhooks = [
            wh for wh in webhooks
            if event_type in wh.events or "*" in wh.events
        ]

        if not matching_webhooks:
            return 0

        # Construct canonical Webhook payload
        canonical_payload = {
            "event_id": event_id,
            "event_type": event_type,
            "workspace_id": str(workspace_id),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": payload_data,
            "version": "v1",
        }
        payload_json = json.dumps(canonical_payload, default=str)

        dispatched = 0
        from app.workers.celery_app import celery_app
        for wh in matching_webhooks:
            celery_app.send_task(
                "heyzen.tasks.maintenance.deliver_webhook",
                args=[
                    str(wh.id),
                    event_id,
                    event_type,
                    wh.url,
                    payload_json,
                    wh.secret,
                ],
                queue="maintenance",
            )
            dispatched += 1

        logger.info(
            "Dispatched event %s (%s) to %d webhooks in workspace %s",
            event_id,
            event_type,
            dispatched,
            workspace_id,
        )
        return dispatched
