"""Workspace, membership, ownership transfer, and invitation management endpoints."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, Path, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission, require_role
from app.core.config import get_settings
from app.core.permissions import WorkspaceRole
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.models.avatar import Avatar, AvatarLook
from app.models.voice import Voice
from app.models.project import Project
from app.schemas.workspace import (
    TransferOwnershipRequest,
    WorkspaceCreate,
    WorkspaceInvitationCreate,
    WorkspaceInvitationResponse,
    WorkspaceMemberResponse,
    WorkspaceMemberUpdate,
    WorkspaceResponse,
    WorkspaceRevokeResponse,
    WorkspaceUpdate,
    OnboardingStatusResponse,
    CompleteOnboardingStepRequest,
)
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])
settings = get_settings()


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Workspace",
    description="Creates a new workspace tenant and assigns the authenticated user as Owner.",
)
async def create_workspace(
    payload: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceResponse:
    ws_service = WorkspaceService(db)
    workspace = await ws_service.create_workspace(
        name=payload.name,
        owner_id=current_user.id,
    )
    await db.commit()

    resp = WorkspaceResponse.model_validate(workspace)
    resp.role = WorkspaceRole.OWNER.value
    return resp


@router.get(
    "",
    response_model=List[WorkspaceResponse],
    summary="List User Workspaces",
    description="Lists all workspaces the authenticated user belongs to.",
)
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[WorkspaceResponse]:
    ws_service = WorkspaceService(db)
    workspaces = await ws_service.list_user_workspaces(current_user.id)

    results = []
    for ws, role in workspaces:
        item = WorkspaceResponse.model_validate(ws)
        item.role = role
        results.append(item)
    return results


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="Get Workspace Details",
    description="Fetch details of a specific workspace. Caller must be an active member.",
)
async def get_workspace(
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("workspace.read")),
) -> WorkspaceResponse:
    workspace, member = context
    resp = WorkspaceResponse.model_validate(workspace)
    resp.role = member.role
    return resp


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="Update Workspace",
    description="Update workspace title or status. Requires 'workspace.update' permission.",
)
async def update_workspace(
    payload: WorkspaceUpdate,
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("workspace.update")),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceResponse:
    workspace, member = context
    ws_service = WorkspaceService(db)
    updated = await ws_service.update_workspace(
        workspace_id=workspace.id,
        name=payload.name,
        status=payload.status,
    )
    await db.commit()

    resp = WorkspaceResponse.model_validate(updated)
    resp.role = member.role
    return resp


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-Delete Workspace",
    description="Marks workspace as deleted. Requires 'workspace.delete' (Owner only).",
)
async def delete_workspace(
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("workspace.delete")),
    db: AsyncSession = Depends(get_db),
) -> None:
    workspace, _ = context
    ws_service = WorkspaceService(db)
    await ws_service.delete_workspace(workspace.id)
    await db.commit()


# --- Member Management Endpoints ---

@router.get(
    "/{workspace_id}/members",
    response_model=List[WorkspaceMemberResponse],
    summary="List Workspace Members",
    description="List all members of the workspace. Requires 'workspace.read' permission.",
)
async def list_members(
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("workspace.read")),
    db: AsyncSession = Depends(get_db),
) -> List[WorkspaceMemberResponse]:
    workspace, _ = context
    ws_service = WorkspaceService(db)
    members = await ws_service.list_members(workspace.id)

    return [
        WorkspaceMemberResponse(
            id=member.id,
            workspace_id=member.workspace_id,
            user_id=user.id,
            email=user.email,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            role=member.role,
            status=member.status,
            joined_at=member.joined_at,
        )
        for member, user in members
    ]


@router.patch(
    "/{workspace_id}/members/{user_id}",
    response_model=WorkspaceMemberResponse,
    summary="Update Member Role",
    description="Update a member's role. Requires 'workspace.manage_members' permission.",
)
async def update_member_role(
    payload: WorkspaceMemberUpdate,
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    user_id: uuid.UUID = Path(..., description="Target Workspace Member User UUID", examples=["11111111-1111-1111-1111-111111111111"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("workspace.manage_members")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceMemberResponse:
    workspace, _ = context
    ws_service = WorkspaceService(db)
    member = await ws_service.update_member_role(
        workspace_id=workspace.id,
        actor_id=current_user.id,
        target_user_id=user_id,
        new_role=payload.role.value,
    )
    await db.commit()

    # Fetch user for response representation
    user = await ws_service.repo.session.get(User, user_id)
    return WorkspaceMemberResponse(
        id=member.id,
        workspace_id=member.workspace_id,
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        role=member.role,
        status=member.status,
        joined_at=member.joined_at,
    )


@router.delete(
    "/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove Workspace Member",
    description="Removes a member from the workspace. Owner cannot be removed.",
)
async def remove_member(
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    user_id: uuid.UUID = Path(..., description="Target Workspace Member User UUID", examples=["11111111-1111-1111-1111-111111111111"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(get_current_user),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    ws_service = WorkspaceService(db)
    # Check permissions: caller must either have manage_members OR be removing themselves
    caller_member = await ws_service.repo.get_member(workspace_id, current_user.id)
    if not caller_member:
        return

    is_self = current_user.id == user_id
    has_manage = caller_member.role in (WorkspaceRole.OWNER.value, WorkspaceRole.ADMIN.value)

    if not is_self and not has_manage:
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException("Permission 'workspace.manage_members' required to remove other members.")

    await ws_service.remove_member(
        workspace_id=workspace_id,
        actor_id=current_user.id,
        target_user_id=user_id,
    )
    await db.commit()


@router.post(
    "/{workspace_id}/transfer-ownership",
    response_model=WorkspaceResponse,
    summary="Transfer Workspace Ownership",
    description="Atomically transfers workspace ownership to another active member. Owner only.",
)
async def transfer_ownership(
    payload: TransferOwnershipRequest,
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_role(WorkspaceRole.OWNER)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceResponse:
    workspace, member = context
    ws_service = WorkspaceService(db)
    updated = await ws_service.transfer_ownership(
        workspace_id=workspace.id,
        current_owner_id=current_user.id,
        target_user_id=payload.target_user_id,
    )
    await db.commit()

    resp = WorkspaceResponse.model_validate(updated)
    resp.role = WorkspaceRole.ADMIN.value  # Previous owner is demoted to Admin
    return resp


# --- Workspace Invitations Endpoints ---

@router.post(
    "/{workspace_id}/invitations",
    response_model=WorkspaceInvitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite Member",
    description="Creates an invitation. Returns token only in development/testing mode.",
)
async def create_invitation(
    payload: WorkspaceInvitationCreate,
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("workspace.manage_members")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceInvitationResponse:
    workspace, _ = context
    ws_service = WorkspaceService(db)
    invitation, raw_token = await ws_service.create_invitation(
        workspace_id=workspace.id,
        actor_id=current_user.id,
        email=payload.email,
        role=payload.role.value,
    )
    await db.commit()

    resp = WorkspaceInvitationResponse.model_validate(invitation)
    # Include raw token ONLY in non-production environments to facilitate automated tests
    if settings.APP_ENV != "production" or settings.DEBUG:
        resp.invitation_token = raw_token
    return resp


@router.get(
    "/{workspace_id}/invitations",
    response_model=List[WorkspaceInvitationResponse],
    summary="List Pending Invitations",
    description="Lists pending invitations. Requires 'workspace.manage_members'.",
)
async def list_invitations(
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("workspace.manage_members")),
    db: AsyncSession = Depends(get_db),
) -> List[WorkspaceInvitationResponse]:
    workspace, _ = context
    ws_service = WorkspaceService(db)
    invitations = await ws_service.list_invitations(workspace.id)
    return [WorkspaceInvitationResponse.model_validate(inv) for inv in invitations]


@router.post(
    "/{workspace_id}/invitations/{invitation_id}/revoke",
    response_model=WorkspaceRevokeResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke Invitation",
    description="Revokes an unaccepted invitation. Requires 'workspace.manage_members'.",
)
async def revoke_invitation(
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    invitation_id: uuid.UUID = Path(..., description="Target Invitation UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("workspace.manage_members")),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceRevokeResponse:
    workspace, _ = context
    ws_service = WorkspaceService(db)
    await ws_service.revoke_invitation(workspace.id, invitation_id)
    await db.commit()
    return WorkspaceRevokeResponse(status="ok", message="Invitation revoked successfully.")


@router.get(
    "/{workspace_id}/onboarding",
    response_model=OnboardingStatusResponse,
    summary="Get Onboarding Setup Status",
    description="Retrieves the 4-step account setup progress derived from real workspace entity state.",
)
async def get_onboarding_status(
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("workspace.read")),
    db: AsyncSession = Depends(get_db),
) -> OnboardingStatusResponse:
    workspace, _ = context

    # Check Step 1: Digital Twin (Custom or Digital Twin avatar created in workspace)
    avatar_q = (
        select(func.count())
        .select_from(Avatar)
        .where(
            Avatar.workspace_id == workspace.id,
            Avatar.deleted_at.is_(None),
            (Avatar.avatar_type.in_(["digital_twin", "custom"])) | (Avatar.name.ilike("%digital twin%")),
        )
    )
    avatar_count = (await db.execute(avatar_q)).scalar() or 0
    step_1 = avatar_count > 0

    # Check Step 2: Voice (Custom or cloned voice in workspace)
    voice_q = (
        select(func.count())
        .select_from(Voice)
        .where(
            Voice.workspace_id == workspace.id,
            Voice.deleted_at.is_(None),
            Voice.voice_type.in_(["cloned", "custom"]),
        )
    )
    voice_count = (await db.execute(voice_q)).scalar() or 0
    step_2 = voice_count > 0

    # Check Step 3: Look (Avatar looks created in workspace)
    look_q = (
        select(func.count())
        .select_from(AvatarLook)
        .join(Avatar, AvatarLook.avatar_id == Avatar.id)
        .where(
            Avatar.workspace_id == workspace.id,
            Avatar.deleted_at.is_(None),
        )
    )
    look_count = (await db.execute(look_q)).scalar() or 0
    step_3 = look_count > 0

    # Check Step 4: First Video (Projects in workspace)
    project_q = (
        select(func.count())
        .select_from(Project)
        .where(
            Project.workspace_id == workspace.id,
            Project.deleted_at.is_(None),
        )
    )
    project_count = (await db.execute(project_q)).scalar() or 0
    step_4 = project_count > 0

    completed_steps = []
    if step_1:
        completed_steps.append(1)
    if step_2:
        completed_steps.append(2)
    if step_3:
        completed_steps.append(3)
    if step_4:
        completed_steps.append(4)

    return OnboardingStatusResponse(
        step_1_digital_twin=step_1,
        step_2_voice=step_2,
        step_3_look=step_3,
        step_4_video=step_4,
        completed_steps=completed_steps,
        completed_count=len(completed_steps),
        total_steps=4,
        is_step_2_unlocked=step_1,
        is_step_3_unlocked=step_1,
        is_step_4_unlocked=step_2 or step_3,
    )


@router.post(
    "/{workspace_id}/onboarding/complete-step",
    response_model=OnboardingStatusResponse,
    summary="Complete Onboarding Step",
    description="Explicitly completes an onboarding step and ensures required workspace entity records exist.",
)
async def complete_onboarding_step(
    payload: CompleteOnboardingStepRequest,
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("workspace.read")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OnboardingStatusResponse:
    workspace, _ = context
    step = payload.step

    if step == 1:
        # Ensure a digital twin avatar exists
        check_q = (
            select(Avatar)
            .where(
                Avatar.workspace_id == workspace.id,
                Avatar.deleted_at.is_(None),
                (Avatar.avatar_type.in_(["digital_twin", "custom"])) | (Avatar.name.ilike("%digital twin%")),
            )
            .limit(1)
        )
        existing = (await db.execute(check_q)).scalar_one_or_none()
        if not existing:
            new_avatar = Avatar(
                workspace_id=workspace.id,
                created_by=current_user.id,
                name="My Digital Twin",
                description="Recorded personal digital twin avatar",
                avatar_type="digital_twin",
                status="ready",
                visibility="workspace",
                provider="mock",
                provider_reference="digital-twin",
                provider_metadata={"category": "Personal", "gender": "neutral"},
            )
            db.add(new_avatar)
            await db.commit()

    elif step == 2:
        # Ensure a custom/cloned voice exists
        check_q = (
            select(Voice)
            .where(
                Voice.workspace_id == workspace.id,
                Voice.deleted_at.is_(None),
                Voice.voice_type.in_(["cloned", "custom"]),
            )
            .limit(1)
        )
        existing = (await db.execute(check_q)).scalar_one_or_none()
        if not existing:
            new_voice = Voice(
                workspace_id=workspace.id,
                created_by=current_user.id,
                name="My Polished Voice",
                description="Custom polished voice profile",
                voice_type="cloned",
                language="en",
                gender="neutral",
                provider="mock",
            )
            db.add(new_voice)
            await db.commit()

    elif step == 3:
        # Ensure a custom look exists
        check_avatar_q = (
            select(Avatar)
            .where(
                Avatar.workspace_id == workspace.id,
                Avatar.deleted_at.is_(None),
            )
            .limit(1)
        )
        target_avatar = (await db.execute(check_avatar_q)).scalar_one_or_none()
        if target_avatar:
            new_look = AvatarLook(
                avatar_id=target_avatar.id,
                name="Casual Studio Look",
                description="Custom look created in Design Look Studio",
                status="ready",
                configuration={"pose": "half_body", "style": "casual_studio"},
            )
            db.add(new_look)
            await db.commit()

    elif step == 4:
        # Ensure a project exists
        check_proj_q = (
            select(Project)
            .where(
                Project.workspace_id == workspace.id,
                Project.deleted_at.is_(None),
            )
            .limit(1)
        )
        existing_proj = (await db.execute(check_proj_q)).scalar_one_or_none()
        if not existing_proj:
            new_proj = Project(
                workspace_id=workspace.id,
                created_by=current_user.id,
                title="My First AI Video",
                project_type="avatar_video",
                status="draft",
                aspect_ratio="16:9",
                width=1920,
                height=1080,
                fps=30,
            )
            db.add(new_proj)
            await db.commit()

    return await get_onboarding_status(workspace_id=workspace_id, context=context, db=db)

