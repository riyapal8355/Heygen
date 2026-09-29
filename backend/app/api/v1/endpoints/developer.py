"""Workspace-scoped Developer API Keys and Webhooks management endpoints."""

import uuid
from typing import Optional, Tuple
from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.developer import (
    ApiKeyCreatedResponse,
    ApiKeyCreateRequest,
    ApiKeyListResponse,
    ApiKeyResponse,
    WebhookCreatedResponse,
    WebhookCreateRequest,
    WebhookDeliveryListResponse,
    WebhookDeliveryResponse,
    WebhookListResponse,
    WebhookResponse,
    WebhookTestResponse,
    WebhookUpdateRequest,
)
from app.services.developer_service import DeveloperService

router = APIRouter()
api_key_router = APIRouter(prefix="/workspaces", tags=["API Keys", "Developer"])
webhook_router = APIRouter(prefix="/workspaces", tags=["Webhooks", "Developer"])


# =============================================================================
# API Key Management Endpoints
# =============================================================================

@api_key_router.post(
    "/{workspace_id}/developer/api-keys",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Developer API Key",
    description="Generate a new workspace developer API key. Plaintext secret is returned ONCE.",
)
async def create_api_key(
    request: ApiKeyCreateRequest,
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    workspace_context: Tuple[Workspace, WorkspaceMember] = Depends(require_permission("api_key.create")),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreatedResponse:
    workspace, member = workspace_context
    service = DeveloperService(db)
    api_key, plaintext_secret = await service.create_api_key(
        workspace_id=workspace.id,
        user_id=member.user_id,
        request=request,
    )

    return ApiKeyCreatedResponse(
        id=api_key.id,
        workspace_id=api_key.workspace_id,
        name=api_key.name,
        prefix=api_key.prefix,
        secret_key=plaintext_secret,
        environment=api_key.environment,
        permissions=api_key.permissions,
        status=api_key.status,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
    )


@api_key_router.get(
    "/{workspace_id}/developer/api-keys",
    response_model=ApiKeyListResponse,
    summary="List Developer API Keys",
    description="List all developer API keys for the workspace. Never exposes plaintext secrets or hashes.",
)
async def list_api_keys(
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    workspace_context: Tuple[Workspace, WorkspaceMember] = Depends(require_permission("api_key.read")),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyListResponse:
    workspace, _ = workspace_context
    service = DeveloperService(db)
    items, total = await service.list_api_keys(workspace_id=workspace.id, limit=limit, offset=offset)

    return ApiKeyListResponse(
        items=[ApiKeyResponse.model_validate(k) for k in items],
        total=total,
    )


@api_key_router.get(
    "/{workspace_id}/developer/api-keys/{key_id}",
    response_model=ApiKeyResponse,
    summary="Get Developer API Key",
    description="Retrieve safe metadata for a specific API key.",
)
async def get_api_key(
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    key_id: uuid.UUID = Path(..., description="Target Developer API Key UUID"),
    workspace_context: Tuple[Workspace, WorkspaceMember] = Depends(require_permission("api_key.read")),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyResponse:
    workspace, _ = workspace_context
    service = DeveloperService(db)
    api_key = await service.get_api_key(workspace_id=workspace.id, key_id=key_id)
    return ApiKeyResponse.model_validate(api_key)


@api_key_router.delete(
    "/{workspace_id}/developer/api-keys/{key_id}",
    response_model=ApiKeyResponse,
    summary="Revoke Developer API Key",
    description="Revoke an API key. Once revoked, it can no longer authenticate.",
)
async def revoke_api_key(
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    key_id: uuid.UUID = Path(..., description="Target Developer API Key UUID"),
    workspace_context: Tuple[Workspace, WorkspaceMember] = Depends(require_permission("api_key.revoke")),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyResponse:
    workspace, _ = workspace_context
    service = DeveloperService(db)
    revoked = await service.revoke_api_key(workspace_id=workspace.id, key_id=key_id)
    return ApiKeyResponse.model_validate(revoked)


# =============================================================================
# Webhook Management Endpoints
# =============================================================================

@webhook_router.post(
    "/{workspace_id}/developer/webhooks",
    response_model=WebhookCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Webhook Endpoint",
    description="Register a new webhook endpoint. Plaintext signing secret is returned ONCE.",
)
async def create_webhook(
    request: WebhookCreateRequest,
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    workspace_context: Tuple[Workspace, WorkspaceMember] = Depends(require_permission("webhook.create")),
    db: AsyncSession = Depends(get_db),
) -> WebhookCreatedResponse:
    workspace, member = workspace_context
    service = DeveloperService(db)
    webhook, secret = await service.create_webhook(
        workspace_id=workspace.id,
        user_id=member.user_id,
        request=request,
    )

    return WebhookCreatedResponse(
        id=webhook.id,
        workspace_id=webhook.workspace_id,
        url=webhook.url,
        secret=secret,
        events=webhook.events,
        status=webhook.status,
        description=webhook.description,
        created_at=webhook.created_at,
    )


@webhook_router.get(
    "/{workspace_id}/developer/webhooks",
    response_model=WebhookListResponse,
    summary="List Webhooks",
    description="List all registered webhooks for the workspace.",
)
async def list_webhooks(
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    status_filter: Optional[str] = Query(None, alias="status"),
    workspace_context: Tuple[Workspace, WorkspaceMember] = Depends(require_permission("webhook.read")),
    db: AsyncSession = Depends(get_db),
) -> WebhookListResponse:
    workspace, _ = workspace_context
    service = DeveloperService(db)
    webhooks = await service.list_webhooks(workspace_id=workspace.id, status=status_filter)

    return WebhookListResponse(
        items=[WebhookResponse.model_validate(w) for w in webhooks],
        total=len(webhooks),
    )


@webhook_router.get(
    "/{workspace_id}/developer/webhooks/{webhook_id}",
    response_model=WebhookResponse,
    summary="Get Webhook",
    description="Retrieve webhook metadata.",
)
async def get_webhook(
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    webhook_id: uuid.UUID = Path(..., description="Target Webhook Subscription UUID"),
    workspace_context: Tuple[Workspace, WorkspaceMember] = Depends(require_permission("webhook.read")),
    db: AsyncSession = Depends(get_db),
) -> WebhookResponse:
    workspace, _ = workspace_context
    service = DeveloperService(db)
    webhook = await service.get_webhook(workspace_id=workspace.id, webhook_id=webhook_id)
    return WebhookResponse.model_validate(webhook)


@webhook_router.patch(
    "/{workspace_id}/developer/webhooks/{webhook_id}",
    response_model=WebhookResponse,
    summary="Update Webhook",
    description="Update destination URL, event subscriptions, or description.",
)
async def update_webhook(
    request: WebhookUpdateRequest,
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    webhook_id: uuid.UUID = Path(..., description="Target Webhook Subscription UUID"),
    workspace_context: Tuple[Workspace, WorkspaceMember] = Depends(require_permission("webhook.manage")),
    db: AsyncSession = Depends(get_db),
) -> WebhookResponse:
    workspace, _ = workspace_context
    service = DeveloperService(db)
    updated = await service.update_webhook(
        workspace_id=workspace.id,
        webhook_id=webhook_id,
        request=request,
    )
    return WebhookResponse.model_validate(updated)


@webhook_router.delete(
    "/{workspace_id}/developer/webhooks/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete / Revoke Webhook",
    description="Revoke and soft-delete a registered webhook endpoint.",
)
async def delete_webhook(
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    webhook_id: uuid.UUID = Path(..., description="Target Webhook Subscription UUID"),
    workspace_context: Tuple[Workspace, WorkspaceMember] = Depends(require_permission("webhook.manage")),
    db: AsyncSession = Depends(get_db),
) -> None:
    workspace, _ = workspace_context
    service = DeveloperService(db)
    await service.delete_webhook(workspace_id=workspace.id, webhook_id=webhook_id)


@webhook_router.get(
    "/{workspace_id}/developer/webhooks/{webhook_id}/deliveries",
    response_model=WebhookDeliveryListResponse,
    summary="List Webhook Deliveries",
    description="Retrieve delivery attempt history and latency metrics for a webhook.",
)
async def list_webhook_deliveries(
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    webhook_id: uuid.UUID = Path(..., description="Target Webhook Subscription UUID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    workspace_context: Tuple[Workspace, WorkspaceMember] = Depends(require_permission("webhook.read")),
    db: AsyncSession = Depends(get_db),
) -> WebhookDeliveryListResponse:
    workspace, _ = workspace_context
    service = DeveloperService(db)
    items, total = await service.list_deliveries(
        workspace_id=workspace.id,
        webhook_id=webhook_id,
        limit=limit,
        offset=offset,
    )

    return WebhookDeliveryListResponse(
        items=[WebhookDeliveryResponse.model_validate(d) for d in items],
        total=total,
    )


@webhook_router.post(
    "/{workspace_id}/developer/webhooks/{webhook_id}/test",
    response_model=WebhookTestResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger Test Webhook Ping",
    description="Dispatch a signed test event to the registered webhook endpoint.",
)
async def test_webhook(
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    webhook_id: uuid.UUID = Path(..., description="Target Webhook Subscription UUID"),
    workspace_context: Tuple[Workspace, WorkspaceMember] = Depends(require_permission("webhook.manage")),
    db: AsyncSession = Depends(get_db),
) -> WebhookTestResponse:
    workspace, _ = workspace_context
    service = DeveloperService(db)
    webhook = await service.get_webhook(workspace_id=workspace.id, webhook_id=webhook_id)

    event_id = f"evt_test_{uuid.uuid4().hex[:12]}"
    await service.dispatch_event_webhooks(
        workspace_id=workspace.id,
        event_id=event_id,
        event_type="webhook.test",
        payload_data={"message": "HeyZen Webhook Integration Test Ping", "webhook_id": str(webhook.id)},
    )

    return WebhookTestResponse(
        status="enqueued",
        event_id=event_id,
        destination_url=webhook.url,
    )



router.include_router(api_key_router)
router.include_router(webhook_router)

