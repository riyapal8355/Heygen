"""Workspace and Session repository encapsulating database queries and mutations."""

import hashlib
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictException, NotFoundException
from app.core.permissions import WorkspaceRole
from app.models.user import User, UserSession
from app.models.workspace import Workspace, WorkspaceInvitation, WorkspaceMember


class WorkspaceRepository:
    """Data access object for Workspaces, Members, Sessions, and Invitations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # --- Workspaces ---

    async def create_workspace(
        self,
        name: str,
        slug: str,
        owner_id: uuid.UUID,
    ) -> Workspace:
        """Create a new workspace."""
        workspace = Workspace(
            name=name.strip(),
            slug=slug.strip().lower(),
            owner_id=owner_id,
            status="active",
        )
        self.session.add(workspace)
        await self.session.flush()
        return workspace

    async def get_by_id(
        self,
        workspace_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> Optional[Workspace]:
        """Fetch workspace by UUID."""
        stmt = select(Workspace).where(Workspace.id == workspace_id)
        if not include_deleted:
            stmt = stmt.where(Workspace.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Optional[Workspace]:
        """Fetch workspace by URL slug."""
        stmt = select(Workspace).where(
            Workspace.slug == slug.strip().lower(),
            Workspace.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_workspaces_for_user(
        self,
        user_id: uuid.UUID,
    ) -> List[Tuple[Workspace, str]]:
        """List all non-deleted workspaces a user belongs to, alongside their role."""
        stmt = (
            select(Workspace, WorkspaceMember.role)
            .join(WorkspaceMember, Workspace.id == WorkspaceMember.workspace_id)
            .where(
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.status == "active",
                Workspace.deleted_at.is_(None),
            )
            .order_by(Workspace.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def soft_delete_workspace(self, workspace: Workspace) -> None:
        """Mark workspace as soft-deleted."""
        workspace.deleted_at = datetime.now(timezone.utc)
        workspace.status = "pending_deletion"
        await self.session.flush()

    # --- Workspace Members ---

    async def add_member(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str,
        status: str = "active",
    ) -> WorkspaceMember:
        """Add a member to a workspace."""
        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
            status=status,
        )
        self.session.add(member)
        await self.session.flush()
        return member

    async def get_member(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[WorkspaceMember]:
        """Fetch membership record by workspace and user ID."""
        stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_members_with_users(
        self,
        workspace_id: uuid.UUID,
    ) -> List[Tuple[WorkspaceMember, User]]:
        """List all members of a workspace joined with User details."""
        stmt = (
            select(WorkspaceMember, User)
            .join(User, WorkspaceMember.user_id == User.id)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .order_by(WorkspaceMember.joined_at.asc())
        )
        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def update_member_role(
        self,
        member: WorkspaceMember,
        new_role: str,
    ) -> WorkspaceMember:
        """Update role of an existing member."""
        member.role = new_role
        member.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return member

    async def remove_member(self, member: WorkspaceMember) -> None:
        """Remove a member from the workspace."""
        await self.session.delete(member)
        await self.session.flush()

    async def transfer_ownership(
        self,
        workspace_id: uuid.UUID,
        current_owner_id: uuid.UUID,
        target_user_id: uuid.UUID,
    ) -> Tuple[Workspace, WorkspaceMember, WorkspaceMember]:
        """Atomically transfer workspace ownership to another active member.
        
        Uses row locking (with_for_update) to prevent concurrent split-brain ownership.
        """
        # 1. Lock and fetch workspace
        ws_stmt = (
            select(Workspace)
            .where(Workspace.id == workspace_id, Workspace.deleted_at.is_(None))
            .with_for_update()
        )
        ws_result = await self.session.execute(ws_stmt)
        workspace = ws_result.scalar_one_or_none()
        if not workspace:
            raise NotFoundException(message="Workspace not found.", code="WORKSPACE_NOT_FOUND")

        if workspace.owner_id != current_owner_id:
            raise ConflictException(message="Only the workspace owner can transfer ownership.", code="NOT_OWNER")

        # 2. Lock and fetch target member
        target_member = await self.get_member(workspace_id, target_user_id)
        if not target_member or target_member.status != "active":
            raise NotFoundException(message="Target member not found or inactive in this workspace.", code="MEMBER_NOT_FOUND")

        # 3. Lock and fetch current owner member record
        current_member = await self.get_member(workspace_id, current_owner_id)
        if not current_member:
            raise NotFoundException(message="Current owner membership not found.", code="MEMBER_NOT_FOUND")

        # 4. Perform atomic update
        workspace.owner_id = target_user_id
        workspace.updated_at = datetime.now(timezone.utc)

        target_member.role = WorkspaceRole.OWNER.value
        target_member.updated_at = datetime.now(timezone.utc)

        current_member.role = WorkspaceRole.ADMIN.value
        current_member.updated_at = datetime.now(timezone.utc)

        await self.session.flush()
        return workspace, target_member, current_member

    # --- User Sessions ---

    async def create_session(
        self,
        user_id: uuid.UUID,
        refresh_token_hash: str,
        expires_at: datetime,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> UserSession:
        """Create a new user session storing the hashed refresh token."""
        session = UserSession(
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
            user_agent=user_agent[:512] if user_agent else None,
            ip_address=ip_address[:64] if ip_address else None,
        )
        self.session.add(session)
        await self.session.flush()
        return session

    async def get_session_by_hash(self, token_hash: str) -> Optional[UserSession]:
        """Fetch session by SHA-256 hash."""
        stmt = (
            select(UserSession)
            .where(UserSession.refresh_token_hash == token_hash)
            .options(selectinload(UserSession.user))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_session(self, session: UserSession) -> None:
        """Mark session as revoked."""
        session.revoked_at = datetime.now(timezone.utc)
        await self.session.flush()

    # --- Workspace Invitations ---

    async def create_invitation(
        self,
        workspace_id: uuid.UUID,
        email: str,
        role: str,
        token_hash: str,
        created_by: uuid.UUID,
        expires_at: datetime,
    ) -> WorkspaceInvitation:
        """Create an invitation record."""
        invitation = WorkspaceInvitation(
            workspace_id=workspace_id,
            email=email.strip().lower(),
            role=role,
            token_hash=token_hash,
            created_by=created_by,
            expires_at=expires_at,
            status="pending",
        )
        self.session.add(invitation)
        await self.session.flush()
        return invitation

    async def get_invitation_by_token_hash(self, token_hash: str) -> Optional[WorkspaceInvitation]:
        """Fetch invitation by SHA-256 hash."""
        stmt = (
            select(WorkspaceInvitation)
            .where(WorkspaceInvitation.token_hash == token_hash)
            .options(selectinload(WorkspaceInvitation.workspace))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_pending_invitations(self, workspace_id: uuid.UUID) -> List[WorkspaceInvitation]:
        """List active pending invitations for a workspace."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(WorkspaceInvitation)
            .where(
                WorkspaceInvitation.workspace_id == workspace_id,
                WorkspaceInvitation.status == "pending",
                WorkspaceInvitation.expires_at > now,
            )
            .order_by(WorkspaceInvitation.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
