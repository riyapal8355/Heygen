"""Workspace domain service managing lifecycle, members, RBAC, ownership, and invitations."""

import hashlib
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.core.permissions import WorkspaceRole
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceInvitation, WorkspaceMember
from app.repositories.workspace import WorkspaceRepository


class WorkspaceService:
    """Encapsulates workspace business logic and membership rules."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = WorkspaceRepository(session)

    def _hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _generate_slug(self, name: str) -> str:
        base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        if not base:
            base = "workspace"
        unique_suffix = secrets.token_hex(3)
        return f"{base[:40]}-{unique_suffix}"

    async def create_workspace(
        self,
        name: str,
        owner_id: uuid.UUID,
    ) -> Workspace:
        """Create a new workspace and assign caller as Owner."""
        slug = self._generate_slug(name)
        workspace = await self.repo.create_workspace(
            name=name,
            slug=slug,
            owner_id=owner_id,
        )
        await self.repo.add_member(
            workspace_id=workspace.id,
            user_id=owner_id,
            role=WorkspaceRole.OWNER.value,
            status="active",
        )
        return workspace

    async def get_workspace(self, workspace_id: uuid.UUID) -> Workspace:
        """Fetch active workspace or raise 404."""
        workspace = await self.repo.get_by_id(workspace_id)
        if not workspace:
            raise NotFoundException(message="Workspace not found.", code="WORKSPACE_NOT_FOUND")
        return workspace

    async def list_user_workspaces(self, user_id: uuid.UUID) -> List[Tuple[Workspace, str]]:
        """List all workspaces the user actively belongs to."""
        return await self.repo.list_workspaces_for_user(user_id)

    async def update_workspace(
        self,
        workspace_id: uuid.UUID,
        name: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Workspace:
        """Update workspace attributes."""
        workspace = await self.get_workspace(workspace_id)
        if name is not None:
            workspace.name = name.strip()
        if status is not None:
            workspace.status = status
        workspace.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return workspace

    async def delete_workspace(self, workspace_id: uuid.UUID) -> None:
        """Soft-delete workspace."""
        workspace = await self.get_workspace(workspace_id)
        await self.repo.soft_delete_workspace(workspace)

    # --- Membership Management ---

    async def list_members(self, workspace_id: uuid.UUID) -> List[Tuple[WorkspaceMember, User]]:
        """List all members joined with their User account information."""
        return await self.repo.list_members_with_users(workspace_id)

    async def update_member_role(
        self,
        workspace_id: uuid.UUID,
        actor_id: uuid.UUID,
        target_user_id: uuid.UUID,
        new_role: str,
    ) -> WorkspaceMember:
        """Update a member's role with protection for the Owner role."""
        workspace = await self.get_workspace(workspace_id)

        # Cannot demote or promote to Owner through regular update
        if target_user_id == workspace.owner_id:
            raise ConflictException(
                message="Cannot modify the Workspace Owner role directly. Use transfer-ownership instead.",
                code="OWNER_ROLE_LOCKED",
            )
        if new_role == WorkspaceRole.OWNER.value:
            raise ConflictException(
                message="Cannot assign Owner role via member update. Use transfer-ownership instead.",
                code="CANNOT_ASSIGN_OWNER",
            )

        member = await self.repo.get_member(workspace_id, target_user_id)
        if not member:
            raise NotFoundException(message="Member not found in this workspace.", code="MEMBER_NOT_FOUND")

        return await self.repo.update_member_role(member, new_role)

    async def remove_member(
        self,
        workspace_id: uuid.UUID,
        actor_id: uuid.UUID,
        target_user_id: uuid.UUID,
    ) -> None:
        """Remove a member or leave a workspace, protecting the Owner account."""
        workspace = await self.get_workspace(workspace_id)

        if target_user_id == workspace.owner_id:
            raise ConflictException(
                message="The workspace owner cannot leave or be removed without transferring ownership first.",
                code="OWNER_CANNOT_LEAVE",
            )

        member = await self.repo.get_member(workspace_id, target_user_id)
        if not member:
            raise NotFoundException(message="Member not found in this workspace.", code="MEMBER_NOT_FOUND")

        await self.repo.remove_member(member)

    async def transfer_ownership(
        self,
        workspace_id: uuid.UUID,
        current_owner_id: uuid.UUID,
        target_user_id: uuid.UUID,
    ) -> Workspace:
        """Execute transactional ownership transfer with row-level locking."""
        if current_owner_id == target_user_id:
            raise ConflictException(message="You are already the owner of this workspace.", code="ALREADY_OWNER")

        workspace, _, _ = await self.repo.transfer_ownership(
            workspace_id=workspace_id,
            current_owner_id=current_owner_id,
            target_user_id=target_user_id,
        )
        return workspace

    # --- Invitations ---

    async def create_invitation(
        self,
        workspace_id: uuid.UUID,
        actor_id: uuid.UUID,
        email: str,
        role: str,
    ) -> Tuple[WorkspaceInvitation, str]:
        """Create a workspace invitation record."""
        cleaned_email = email.strip().lower()

        # 1. Check if user is already a member
        members = await self.repo.list_members_with_users(workspace_id)
        for _, user in members:
            if user.email.lower() == cleaned_email:
                raise ConflictException(
                    message=f"User '{email}' is already a member of this workspace.",
                    code="MEMBER_ALREADY_EXISTS",
                )

        # 2. Generate secure token
        raw_token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        invitation = await self.repo.create_invitation(
            workspace_id=workspace_id,
            email=cleaned_email,
            role=role,
            token_hash=token_hash,
            created_by=actor_id,
            expires_at=expires_at,
        )
        return invitation, raw_token

    async def list_invitations(self, workspace_id: uuid.UUID) -> List[WorkspaceInvitation]:
        """List active pending invitations."""
        return await self.repo.list_pending_invitations(workspace_id)

    async def accept_invitation(
        self,
        raw_token: str,
        user: User,
    ) -> Tuple[Workspace, str]:
        """Redeem invitation token and add user to workspace."""
        token_hash = self._hash_token(raw_token)
        invitation = await self.repo.get_invitation_by_token_hash(token_hash)

        if not invitation or not invitation.is_valid:
            raise ConflictException(
                message="Invitation token is invalid, expired, or already redeemed.",
                code="INVITATION_INVALID",
            )

        workspace = invitation.workspace
        if not workspace or workspace.deleted_at is not None:
            raise NotFoundException(message="The inviting workspace is no longer active.", code="WORKSPACE_NOT_FOUND")

        # Check if already a member
        existing_member = await self.repo.get_member(workspace.id, user.id)
        if not existing_member:
            await self.repo.add_member(
                workspace_id=workspace.id,
                user_id=user.id,
                role=invitation.role,
                status="active",
            )

        # Mark invitation redeemed
        invitation.status = "accepted"
        invitation.accepted_at = datetime.now(timezone.utc)
        await self.session.flush()

        return workspace, invitation.role

    async def revoke_invitation(
        self,
        workspace_id: uuid.UUID,
        invitation_id: uuid.UUID,
    ) -> None:
        """Revoke a pending invitation."""
        invitations = await self.repo.list_pending_invitations(workspace_id)
        target = next((inv for inv in invitations if inv.id == invitation_id), None)
        if not target:
            raise NotFoundException(message="Invitation not found.", code="INVITATION_NOT_FOUND")

        target.status = "revoked"
        target.revoked_at = datetime.now(timezone.utc)
        await self.session.flush()
