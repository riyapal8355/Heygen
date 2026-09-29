"""FastAPI endpoint for AskRhys conversational AI Copilot."""

import uuid
from typing import Tuple
from fastapi import APIRouter, Depends, Header, Path, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_workspace
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.ask_rhys import AskRhysRequest, AskRhysResponse
from app.services.ask_rhys_service import AskRhysService

router = APIRouter(prefix="/workspaces/{workspace_id}/ask-rhys", tags=["Ask Rhys AI", "AI"])



@router.post(
    "",
    response_model=AskRhysResponse,
    status_code=status.HTTP_200_OK,
    summary="Query AskRhys AI Copilot",
    description=(
        "Executes truthful conversational inference via the local CPU Qwen 2.5 0.5B ONNX model. "
        "Enforces workspace isolation, rate limiting, and returns non-mutating project suggestions."
    ),
)
async def ask_rhys(
    request: Request,
    payload: AskRhysRequest,
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    current_user: User = Depends(get_current_user),
    workspace_ctx: Tuple[Workspace, WorkspaceMember] = Depends(get_current_workspace),
    x_request_id: str = Header(None, alias="X-Request-ID"),
    db: AsyncSession = Depends(get_db),
) -> AskRhysResponse:
    """Handle conversational queries directed to Rhys AI Copilot."""
    workspace, _member = workspace_ctx
    service = AskRhysService(db=db)
    return await service.ask(
        workspace_id=workspace.id,
        user_id=current_user.id,
        request=payload,
        request_id=x_request_id or getattr(request.state, "request_id", None),
    )


direct_router = APIRouter(tags=["Ask Rhys AI", "AI"])


@direct_router.post(
    "/ask-rhys/chat",
    response_model=AskRhysResponse,
    status_code=status.HTTP_200_OK,
    summary="Query AskRhys AI Copilot Direct Chat",
    description="Direct endpoint for conversational queries directed to Rhys AI Copilot using X-Workspace-ID header.",
)
async def ask_rhys_direct(
    request: Request,
    payload: AskRhysRequest,
    current_user: User = Depends(get_current_user),
    workspace_ctx: Tuple[Workspace, WorkspaceMember] = Depends(get_current_workspace),
    x_request_id: str = Header(None, alias="X-Request-ID"),
    db: AsyncSession = Depends(get_db),
) -> AskRhysResponse:
    """Handle direct chat queries directed to Rhys AI Copilot."""
    workspace, _member = workspace_ctx
    service = AskRhysService(db=db)
    return await service.ask(
        workspace_id=workspace.id,
        user_id=current_user.id,
        request=payload,
        request_id=x_request_id or getattr(request.state, "request_id", None),
    )

