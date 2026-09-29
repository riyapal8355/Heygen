"""Role-based access control (RBAC) and granular permission definitions."""

from enum import Enum
from typing import Dict, Set


class WorkspaceRole(str, Enum):
    """Supported workspace collaboration roles in descending hierarchy order."""
    OWNER = "owner"
    ADMIN = "admin"
    CREATOR = "creator"
    VIEWER = "viewer"


# Numerical hierarchy score for comparison
ROLE_HIERARCHY: Dict[str, int] = {
    WorkspaceRole.OWNER.value: 40,
    WorkspaceRole.ADMIN.value: 30,
    WorkspaceRole.CREATOR.value: 20,
    WorkspaceRole.VIEWER.value: 10,
}


# Granular application-level permissions mapping
ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    WorkspaceRole.OWNER.value: {
        # Full workspace authority
        "workspace.read",
        "workspace.update",
        "workspace.delete",
        "workspace.manage_members",
        "workspace.transfer_ownership",
        # Project & rendering operations
        "project.read",
        "project.create",
        "project.update",
        "project.delete",
        "project.render",
        # Asset operations
        "asset.read",
        "asset.create",
        "asset.delete",
        # Creative library
        "folder.read",
        "folder.create",
        "folder.update",
        "folder.delete",
        "avatar.read",
        "avatar.create",
        "avatar.update",
        "avatar.delete",
        "voice.read",
        "voice.create",
        "voice.update",
        "voice.delete",
        "template.read",
        "template.create",
        "template.update",
        "template.delete",
        "brand.read",
        "brand.create",
        "brand.update",
        "brand.delete",
        # Job execution
        "job.create",
        "job.read",
        "job.cancel",
        # Platform integration & billing
        "api_key.read",
        "api_key.create",
        "api_key.revoke",
        "webhook.read",
        "webhook.create",
        "webhook.manage",
        "billing.read",
        "billing.manage",
    },
    WorkspaceRole.ADMIN.value: {
        "workspace.read",
        "workspace.update",
        "workspace.manage_members",
        "folder.read",
        "folder.create",
        "folder.update",
        "folder.delete",
        "project.read",
        "project.create",
        "project.update",
        "project.delete",
        "project.render",
        "asset.read",
        "asset.create",
        "asset.delete",
        "avatar.read",
        "avatar.create",
        "avatar.update",
        "avatar.delete",
        "voice.read",
        "voice.create",
        "voice.update",
        "voice.delete",
        "template.read",
        "template.create",
        "template.update",
        "template.delete",
        "brand.read",
        "brand.create",
        "brand.update",
        "brand.delete",
        "job.create",
        "job.read",
        "job.cancel",
        "api_key.read",
        "api_key.create",
        "api_key.revoke",
        "webhook.read",
        "webhook.create",
        "webhook.manage",
        "billing.read",
    },
    WorkspaceRole.CREATOR.value: {
        "workspace.read",
        "folder.read",
        "folder.create",
        "folder.update",
        "folder.delete",
        "project.read",
        "project.create",
        "project.update",
        "project.delete",
        "project.render",
        "asset.read",
        "asset.create",
        "avatar.read",
        "avatar.create",
        "voice.read",
        "voice.create",
        "template.read",
        "template.create",
        "brand.read",
        "job.create",
        "job.read",
        "job.cancel",
    },
    WorkspaceRole.VIEWER.value: {
        "workspace.read",
        "folder.read",
        "project.read",
        "asset.read",
        "avatar.read",
        "voice.read",
        "template.read",
        "brand.read",
        "job.read",
    },
}


def has_permission(role: str, permission: str) -> bool:
    """Evaluate whether a role grants a specific permission string."""
    perms = ROLE_PERMISSIONS.get(role, set())
    return permission in perms


def is_role_at_least(user_role: str, minimum_role: str) -> bool:
    """Check if user_role meets or exceeds minimum_role in hierarchy."""
    user_level = ROLE_HIERARCHY.get(user_role, 0)
    min_level = ROLE_HIERARCHY.get(minimum_role, 0)
    return user_level >= min_level
