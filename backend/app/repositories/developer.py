"""Database repositories for Developer API keys, Webhooks, and Deliveries."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.developer import ApiKey, Webhook, WebhookDelivery


class ApiKeyRepository:
    """PostgreSQL data access repository for workspace API keys."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, api_key: ApiKey) -> ApiKey:
        """Persist a new API key record."""
        self.session.add(api_key)
        await self.session.flush()
        await self.session.refresh(api_key)
        return api_key

    async def get_by_id(
        self,
        key_id: uuid.UUID,
        workspace_id: Optional[uuid.UUID] = None,
    ) -> Optional[ApiKey]:
        """Fetch API key by ID, optionally verifying workspace tenancy boundary."""
        stmt = select(ApiKey).where(
            ApiKey.id == key_id,
            ApiKey.deleted_at.is_(None),
        )
        if workspace_id is not None:
            stmt = stmt.where(ApiKey.workspace_id == workspace_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_prefix(self, prefix: str) -> Optional[ApiKey]:
        """Lookup active API key by its public prefix."""
        stmt = select(ApiKey).where(
            ApiKey.prefix == prefix,
            ApiKey.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[ApiKey], int]:
        """List active/revoked keys for a workspace with total count."""
        base_where = (
            ApiKey.workspace_id == workspace_id,
            ApiKey.deleted_at.is_(None),
        )

        count_stmt = select(func.count(ApiKey.id)).where(*base_where)
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(ApiKey)
            .where(*base_where)
            .order_by(desc(ApiKey.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    async def revoke(self, api_key: ApiKey) -> ApiKey:
        """Mark an API key as revoked."""
        api_key.status = "revoked"
        api_key.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return api_key

    async def update_last_used(self, key_id: uuid.UUID) -> None:
        """Update last_used_at timestamp without full entity re-fetch."""
        stmt = (
            update(ApiKey)
            .where(ApiKey.id == key_id)
            .values(last_used_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)
        await self.session.commit()


class WebhookRepository:
    """PostgreSQL data access repository for registered webhooks."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, webhook: Webhook) -> Webhook:
        """Persist a new webhook endpoint."""
        self.session.add(webhook)
        await self.session.flush()
        await self.session.refresh(webhook)
        return webhook

    async def get_by_id(
        self,
        webhook_id: uuid.UUID,
        workspace_id: Optional[uuid.UUID] = None,
    ) -> Optional[Webhook]:
        """Fetch webhook by ID, optionally verifying workspace tenancy."""
        stmt = select(Webhook).where(
            Webhook.id == webhook_id,
            Webhook.deleted_at.is_(None),
        )
        if workspace_id is not None:
            stmt = stmt.where(Webhook.workspace_id == workspace_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
        status: Optional[str] = None,
    ) -> List[Webhook]:
        """List webhooks for a workspace."""
        stmt = select(Webhook).where(
            Webhook.workspace_id == workspace_id,
            Webhook.deleted_at.is_(None),
        )
        if status is not None:
            stmt = stmt.where(Webhook.status == status)
        stmt = stmt.order_by(desc(Webhook.created_at))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, webhook: Webhook) -> Webhook:
        """Update webhook configuration."""
        webhook.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return webhook

    async def delete(self, webhook: Webhook) -> None:
        """Soft-delete a webhook."""
        webhook.deleted_at = datetime.now(timezone.utc)
        webhook.status = "revoked"
        await self.session.flush()

    async def increment_failure(self, webhook_id: uuid.UUID, max_failures: int = 5) -> None:
        """Increment consecutive failure count; auto-disable if threshold reached."""
        stmt = (
            update(Webhook)
            .where(Webhook.id == webhook_id)
            .values(failure_count=Webhook.failure_count + 1)
        )
        await self.session.execute(stmt)

        # Check if max failures reached
        webhook = await self.get_by_id(webhook_id)
        if webhook and webhook.failure_count >= max_failures:
            webhook.status = "disabled"
            await self.session.flush()
        await self.session.commit()

    async def reset_failure(self, webhook_id: uuid.UUID) -> None:
        """Reset failure counter after successful delivery."""
        stmt = (
            update(Webhook)
            .where(Webhook.id == webhook_id)
            .values(failure_count=0)
        )
        await self.session.execute(stmt)
        await self.session.commit()


class WebhookDeliveryRepository:
    """PostgreSQL data access repository for webhook delivery logs."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, delivery: WebhookDelivery) -> WebhookDelivery:
        """Record a webhook delivery attempt."""
        self.session.add(delivery)
        await self.session.flush()
        await self.session.refresh(delivery)
        return delivery

    async def get_by_id(self, delivery_id: uuid.UUID) -> Optional[WebhookDelivery]:
        """Fetch delivery attempt by ID."""
        stmt = select(WebhookDelivery).where(WebhookDelivery.id == delivery_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_webhook(
        self,
        webhook_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[WebhookDelivery], int]:
        """List deliveries for a webhook with total count."""
        count_stmt = select(func.count(WebhookDelivery.id)).where(
            WebhookDelivery.webhook_id == webhook_id
        )
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(WebhookDelivery)
            .where(WebhookDelivery.webhook_id == webhook_id)
            .order_by(desc(WebhookDelivery.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        items = list(result.scalars().all())
        return items, total
