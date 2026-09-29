"""Creative Library domain tables: Avatars, Looks, Voices, Templates, Versions, BrandKits, Glossaries, Rules

Revision ID: 0004_creative_library
Revises: 0003_projects_folders_assets
Create Date: 2026-09-12 14:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic (must be <= 32 chars).
revision: str = '0004_creative_library'
down_revision: Union[str, None] = '0003_projects_folders_assets'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create avatars table
    op.create_table(
        'avatars',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE', name='fk_avatars_workspace_id'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT', name='fk_avatars_created_by'), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.String(length=512), nullable=True),
        sa.Column('avatar_type', sa.String(length=32), server_default='custom', nullable=False),
        sa.Column('status', sa.String(length=32), server_default='ready', nullable=False),
        sa.Column('visibility', sa.String(length=32), server_default='workspace', nullable=False),
        sa.Column('provider', sa.String(length=64), server_default='mock', nullable=False),
        sa.Column('provider_reference', sa.String(length=255), nullable=True),
        sa.Column('provider_metadata', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('preview_asset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('assets.id', ondelete='SET NULL', name='fk_avatars_preview_asset_id'), nullable=True),
        sa.Column('source_asset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('assets.id', ondelete='SET NULL', name='fk_avatars_source_asset_id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_avatars_workspace_id', 'avatars', ['workspace_id'])
    op.create_index('ix_avatars_created_by', 'avatars', ['created_by'])
    op.create_index('ix_avatars_status', 'avatars', ['status'])
    op.create_index('ix_avatars_workspace_name', 'avatars', ['workspace_id', 'name'])
    op.create_index('ix_avatars_created_at', 'avatars', ['created_at'])

    # 2. Create avatar_looks table
    op.create_table(
        'avatar_looks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('avatar_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('avatars.id', ondelete='CASCADE', name='fk_avatar_looks_avatar_id'), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.String(length=512), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='ready', nullable=False),
        sa.Column('configuration', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('preview_asset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('assets.id', ondelete='SET NULL', name='fk_avatar_looks_preview_asset_id'), nullable=True),
        sa.Column('provider', sa.String(length=64), server_default='mock', nullable=False),
        sa.Column('provider_reference', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('avatar_id', 'name', name='uq_avatar_looks_avatar_name'),
    )
    op.create_index('ix_avatar_looks_avatar_id', 'avatar_looks', ['avatar_id'])
    op.create_index('ix_avatar_looks_created_at', 'avatar_looks', ['created_at'])

    # 3. Create voices table
    op.create_table(
        'voices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE', name='fk_voices_workspace_id'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT', name='fk_voices_created_by'), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.String(length=512), nullable=True),
        sa.Column('voice_type', sa.String(length=32), server_default='preset', nullable=False),
        sa.Column('language', sa.String(length=16), server_default='en', nullable=False),
        sa.Column('gender', sa.String(length=16), server_default='neutral', nullable=False),
        sa.Column('provider', sa.String(length=64), server_default='mock', nullable=False),
        sa.Column('provider_reference', sa.String(length=255), nullable=True),
        sa.Column('provider_metadata', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('preview_asset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('assets.id', ondelete='SET NULL', name='fk_voices_preview_asset_id'), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='ready', nullable=False),
        sa.Column('visibility', sa.String(length=32), server_default='workspace', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_voices_workspace_id', 'voices', ['workspace_id'])
    op.create_index('ix_voices_created_by', 'voices', ['created_by'])
    op.create_index('ix_voices_status', 'voices', ['status'])
    op.create_index('ix_voices_workspace_name', 'voices', ['workspace_id', 'name'])
    op.create_index('ix_voices_workspace_lang_gender', 'voices', ['workspace_id', 'language', 'gender'])
    op.create_index('ix_voices_created_at', 'voices', ['created_at'])

    # 4. Create templates table (without current_version_id FK initially to avoid circular dependency)
    op.create_table(
        'templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE', name='fk_templates_workspace_id'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT', name='fk_templates_created_by'), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.String(length=512), nullable=True),
        sa.Column('category', sa.String(length=64), server_default='marketing', nullable=False),
        sa.Column('status', sa.String(length=32), server_default='active', nullable=False),
        sa.Column('visibility', sa.String(length=32), server_default='workspace', nullable=False),
        sa.Column('thumbnail_asset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('assets.id', ondelete='SET NULL', name='fk_templates_thumbnail_asset_id'), nullable=True),
        sa.Column('configuration', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('current_version_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('revision', sa.Integer(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_templates_workspace_id', 'templates', ['workspace_id'])
    op.create_index('ix_templates_created_by', 'templates', ['created_by'])
    op.create_index('ix_templates_category', 'templates', ['category'])
    op.create_index('ix_templates_status', 'templates', ['status'])
    op.create_index('ix_templates_workspace_name', 'templates', ['workspace_id', 'name'])
    op.create_index('ix_templates_created_at', 'templates', ['created_at'])

    # 5. Create template_versions table
    op.create_table(
        'template_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('templates.id', ondelete='CASCADE', name='fk_template_versions_template_id'), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('document', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT', name='fk_template_versions_created_by'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('template_id', 'revision', name='uq_template_versions_template_revision'),
    )
    op.create_index('ix_template_versions_template_id', 'template_versions', ['template_id'])
    op.create_index('ix_template_versions_template_rev', 'template_versions', ['template_id', 'revision'])

    # 6. Add deferred foreign key constraint to templates.current_version_id
    op.create_foreign_key(
        'fk_templates_current_version_id',
        'templates',
        'template_versions',
        ['current_version_id'],
        ['id'],
        ondelete='SET NULL',
        use_alter=True,
    )

    # 7. Create brand_kits table
    op.create_table(
        'brand_kits',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE', name='fk_brand_kits_workspace_id'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT', name='fk_brand_kits_created_by'), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.String(length=512), nullable=True),
        sa.Column('logo_asset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('assets.id', ondelete='SET NULL', name='fk_brand_kits_logo_asset_id'), nullable=True),
        sa.Column('colors', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('typography', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('is_default', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_brand_kits_workspace_id', 'brand_kits', ['workspace_id'])
    op.create_index('ix_brand_kits_created_by', 'brand_kits', ['created_by'])
    op.create_index('ix_brand_kits_workspace_name', 'brand_kits', ['workspace_id', 'name'])
    op.create_index('ix_brand_kits_created_at', 'brand_kits', ['created_at'])

    # 8. Create brand_glossaries table
    op.create_table(
        'brand_glossaries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE', name='fk_brand_glossaries_workspace_id'), nullable=False),
        sa.Column('brand_kit_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('brand_kits.id', ondelete='CASCADE', name='fk_brand_glossaries_brand_kit_id'), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT', name='fk_brand_glossaries_created_by'), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.String(length=512), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='active', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_brand_glossaries_workspace_id', 'brand_glossaries', ['workspace_id'])
    op.create_index('ix_brand_glossaries_brand_kit_id', 'brand_glossaries', ['brand_kit_id'])
    op.create_index('ix_brand_glossaries_created_by', 'brand_glossaries', ['created_by'])
    op.create_index('ix_brand_glossaries_workspace_name', 'brand_glossaries', ['workspace_id', 'name'])
    op.create_index('ix_brand_glossaries_created_at', 'brand_glossaries', ['created_at'])

    # 9. Create brand_glossary_rules table
    op.create_table(
        'brand_glossary_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('glossary_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('brand_glossaries.id', ondelete='CASCADE', name='fk_brand_glossary_rules_glossary_id'), nullable=False),
        sa.Column('source_term', sa.String(length=255), nullable=False),
        sa.Column('preferred_term', sa.String(length=255), nullable=False),
        sa.Column('forbidden_term', sa.String(length=255), nullable=True),
        sa.Column('source_language', sa.String(length=16), server_default='en', nullable=False),
        sa.Column('target_language', sa.String(length=16), nullable=True),
        sa.Column('case_sensitive', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('status', sa.String(length=32), server_default='active', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_brand_glossary_rules_glossary_id', 'brand_glossary_rules', ['glossary_id'])
    op.create_index('ix_brand_glossary_rules_source', 'brand_glossary_rules', ['source_term'])
    op.create_index('ix_brand_glossary_rules_created_at', 'brand_glossary_rules', ['created_at'])


def downgrade() -> None:
    # Drop in strict reverse dependency order
    op.drop_table('brand_glossary_rules')
    op.drop_table('brand_glossaries')
    op.drop_table('brand_kits')
    op.drop_constraint('fk_templates_current_version_id', 'templates', type_='foreignkey')
    op.drop_table('template_versions')
    op.drop_table('templates')
    op.drop_table('voices')
    op.drop_table('avatar_looks')
    op.drop_table('avatars')
