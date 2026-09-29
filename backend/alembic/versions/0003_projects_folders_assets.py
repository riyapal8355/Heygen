"""Projects, folders, assets, and project versions

Revision ID: 0003_projects_folders_assets
Revises: 0002_workspaces_and_auth
Create Date: 2026-09-12 13:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic (must be <= 32 chars).
revision: str = '0003_projects_folders_assets'
down_revision: Union[str, None] = '0002_workspaces_and_auth'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create folders table
    op.create_table(
        'folders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE', name='fk_folders_workspace_id'), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('folders.id', ondelete='RESTRICT', name='fk_folders_parent_id'), nullable=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT', name='fk_folders_created_by'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_folders_workspace_id', 'folders', ['workspace_id'])
    op.create_index('ix_folders_parent_id', 'folders', ['parent_id'])
    op.create_index('ix_folders_created_by', 'folders', ['created_by'])
    op.create_index('ix_folders_workspace_parent', 'folders', ['workspace_id', 'parent_id'])
    op.create_index('ix_folders_updated_at', 'folders', ['updated_at'])

    # 2. Create assets table
    op.create_table(
        'assets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE', name='fk_assets_workspace_id'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT', name='fk_assets_created_by'), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('storage_bucket', sa.String(length=128), nullable=False),
        sa.Column('storage_key', sa.String(length=512), nullable=False),
        sa.Column('mime_type', sa.String(length=128), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('checksum_sha256', sa.String(length=64), nullable=True),
        sa.Column('asset_type', sa.String(length=32), server_default='other', nullable=False),
        sa.Column('status', sa.String(length=32), server_default='pending_upload', nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_assets_workspace_id', 'assets', ['workspace_id'])
    op.create_index('ix_assets_created_by', 'assets', ['created_by'])
    op.create_index('ix_assets_storage_key', 'assets', ['storage_key'], unique=True)
    op.create_index('ix_assets_asset_type', 'assets', ['asset_type'])
    op.create_index('ix_assets_status', 'assets', ['status'])
    op.create_index('ix_assets_created_at', 'assets', ['created_at'])

    # 3. Create projects table
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE', name='fk_projects_workspace_id'), nullable=False),
        sa.Column('folder_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('folders.id', ondelete='SET NULL', name='fk_projects_folder_id'), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT', name='fk_projects_created_by'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('project_type', sa.String(length=64), server_default='standard', nullable=False),
        sa.Column('status', sa.String(length=32), server_default='draft', nullable=False),
        sa.Column('aspect_ratio', sa.String(length=16), server_default='16:9', nullable=False),
        sa.Column('width', sa.Integer(), server_default='1920', nullable=True),
        sa.Column('height', sa.Integer(), server_default='1080', nullable=True),
        sa.Column('fps', sa.Integer(), server_default='30', nullable=True),
        sa.Column('duration_ms', sa.Integer(), server_default='0', nullable=True),
        sa.Column('thumbnail_asset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('assets.id', ondelete='SET NULL', name='fk_projects_thumbnail_asset_id'), nullable=True),
        sa.Column('current_version_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('revision', sa.Integer(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_projects_workspace_id', 'projects', ['workspace_id'])
    op.create_index('ix_projects_folder_id', 'projects', ['folder_id'])
    op.create_index('ix_projects_created_by', 'projects', ['created_by'])
    op.create_index('ix_projects_status', 'projects', ['status'])
    op.create_index('ix_projects_workspace_updated', 'projects', ['workspace_id', 'updated_at'])
    op.create_index('ix_projects_updated_at', 'projects', ['updated_at'])

    # 4. Create project_versions table
    op.create_table(
        'project_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE', name='fk_project_versions_project_id'), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('document', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT', name='fk_project_versions_created_by'), nullable=False),
        sa.Column('source', sa.String(length=32), server_default='manual', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('project_id', 'revision', name='uq_project_versions_project_revision'),
    )
    op.create_index('ix_project_versions_project_id', 'project_versions', ['project_id'])
    op.create_index('ix_project_versions_project_rev', 'project_versions', ['project_id', 'revision'])

    # 5. Add circular FK from projects.current_version_id to project_versions.id
    op.create_foreign_key(
        'fk_projects_current_version_id',
        'projects',
        'project_versions',
        ['current_version_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_projects_current_version_id', 'projects', type_='foreignkey')
    op.drop_table('project_versions')
    op.drop_table('projects')
    op.drop_table('assets')
    op.drop_table('folders')
