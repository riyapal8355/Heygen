"""Invitation redemption endpoints."""

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.workspace import InvitationAcceptResponse, WorkspaceResponse
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/invitations", tags=["Invitations"])


@router.post(
    "/{token}/accept",
    response_model=InvitationAcceptResponse,
    status_code=status.HTTP_200_OK,
    summary="Accept Workspace Invitation",
    description="Redeems an invitation token and adds the authenticated user to the workspace with the invited role.",
)
async def accept_invitation(
    token: str = Path(..., min_length=16, description="Invitation secret token"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvitationAcceptResponse:
    ws_service = WorkspaceService(db)
    workspace, role = await ws_service.accept_invitation(
        raw_token=token,
        user=current_user,
    )
    await db.commit()

    ws_resp = WorkspaceResponse.model_validate(workspace)
    ws_resp.role = role

    return InvitationAcceptResponse(
        workspace=ws_resp,
        role=role,
        message=f"Successfully joined {workspace.name} as {role}.",
    )
