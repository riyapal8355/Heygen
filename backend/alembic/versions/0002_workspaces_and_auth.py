"""Workspaces, workspace members, user sessions, and workspace invitations

Revision ID: 0002_workspaces_and_auth
Revises: 0001_initial_user_schema
Create Date: 2026-09-12 07:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic (must be <= 32 chars).
revision: str = '0002_workspaces_and_auth'
down_revision: Union[str, None] = '0001_initial_user_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create workspaces table
    op.create_table(
        'workspaces',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('slug', sa.String(length=128), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT', name='fk_workspaces_owner_id'), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='active', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name='pk_workspaces'),
        sa.UniqueConstraint('slug', name='uq_workspaces_slug'),
    )
    op.create_index('idx_workspaces_slug', 'workspaces', ['slug'])
    op.create_index('idx_workspaces_owner_id', 'workspaces', ['owner_id'])
    op.create_index('idx_workspaces_status', 'workspaces', ['status'])

    # 2. Create workspace_members table
    op.create_table(
        'workspace_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE', name='fk_workspace_members_workspace_id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE', name='fk_workspace_members_user_id'), nullable=False),
        sa.Column('role', sa.String(length=32), server_default='creator', nullable=False),
        sa.Column('status', sa.String(length=32), server_default='active', nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_workspace_members'),
        sa.UniqueConstraint('workspace_id', 'user_id', name='uq_workspace_members_ws_user'),
    )
    op.create_index('idx_workspace_members_workspace_id', 'workspace_members', ['workspace_id'])
    op.create_index('idx_workspace_members_user_id', 'workspace_members', ['user_id'])

    # 3. Create user_sessions table
    op.create_table(
        'user_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE', name='fk_user_sessions_user_id'), nullable=False),
        sa.Column('refresh_token_hash', sa.String(length=64), nullable=False),
        sa.Column('user_agent', sa.String(length=512), nullable=True),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_user_sessions'),
        sa.UniqueConstraint('refresh_token_hash', name='uq_user_sessions_refresh_token_hash'),
    )
    op.create_index('idx_user_sessions_user_id', 'user_sessions', ['user_id'])
    op.create_index('idx_user_sessions_token_hash', 'user_sessions', ['refresh_token_hash'])

    # 4. Create workspace_invitations table
    op.create_table(
        'workspace_invitations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE', name='fk_workspace_invitations_workspace_id'), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=32), server_default='creator', nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='pending', nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE', name='fk_workspace_invitations_created_by'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_workspace_invitations'),
        sa.UniqueConstraint('token_hash', name='uq_workspace_invitations_token_hash'),
    )
    op.create_index('idx_workspace_invitations_workspace_id', 'workspace_invitations', ['workspace_id'])
    op.create_index('idx_workspace_invitations_email', 'workspace_invitations', ['email'])


def downgrade() -> None:
    op.drop_table('workspace_invitations')
    op.drop_table('user_sessions')
    op.drop_table('workspace_members')
    op.drop_table('workspaces')
