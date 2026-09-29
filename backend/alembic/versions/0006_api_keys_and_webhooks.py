"""Developer API keys and webhooks tables: api_keys, webhooks, webhook_deliveries

Revision ID: 0006_api_keys_and_webhooks
Revises: 0005_jobs_task_pipeline
Create Date: 2026-09-17 16:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic (must be <= 32 chars).
revision: str = '0006_api_keys_and_webhooks'
down_revision: Union[str, None] = '0005_jobs_task_pipeline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create api_keys table
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE', name='fk_api_keys_workspace_id'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL', name='fk_api_keys_created_by'), nullable=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('prefix', sa.String(length=32), nullable=False),
        sa.Column('key_hash', sa.String(length=64), nullable=False),
        sa.Column('environment', sa.String(length=32), server_default='production', nullable=False),
        sa.Column('permissions', sa.String(length=32), server_default='full', nullable=False),
        sa.Column('status', sa.String(length=32), server_default='active', nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_api_keys_workspace_id', 'api_keys', ['workspace_id'])
    op.create_index('ix_api_keys_prefix', 'api_keys', ['prefix'])
    op.create_index('ix_api_keys_key_hash', 'api_keys', ['key_hash'])
    op.create_index('ix_api_keys_status', 'api_keys', ['status'])
    op.create_index('ix_api_keys_workspace_status', 'api_keys', ['workspace_id', 'status'])

    # 2. Create webhooks table
    op.create_table(
        'webhooks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE', name='fk_webhooks_workspace_id'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL', name='fk_webhooks_created_by'), nullable=True),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('secret', sa.String(length=128), nullable=False),
        sa.Column('events', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='active', nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('failure_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_webhooks_workspace_id', 'webhooks', ['workspace_id'])
    op.create_index('ix_webhooks_status', 'webhooks', ['status'])
    op.create_index('ix_webhooks_workspace_status', 'webhooks', ['workspace_id', 'status'])

    # 3. Create webhook_deliveries table
    op.create_table(
        'webhook_deliveries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('webhook_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('webhooks.id', ondelete='CASCADE', name='fk_webhook_deliveries_webhook_id'), nullable=False),
        sa.Column('event_id', sa.String(length=64), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('response_status_code', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='delivered', nullable=False),
        sa.Column('attempt', sa.Integer(), server_default='1', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_webhook_deliveries_webhook_id', 'webhook_deliveries', ['webhook_id'])
    op.create_index('ix_webhook_deliveries_event_id', 'webhook_deliveries', ['event_id'])
    op.create_index('ix_webhook_deliveries_status', 'webhook_deliveries', ['status'])
    op.create_index('ix_webhook_deliveries_created_at', 'webhook_deliveries', ['created_at'])


def downgrade() -> None:
    # Drop webhook_deliveries
    op.drop_index('ix_webhook_deliveries_created_at', table_name='webhook_deliveries')
    op.drop_index('ix_webhook_deliveries_status', table_name='webhook_deliveries')
    op.drop_index('ix_webhook_deliveries_event_id', table_name='webhook_deliveries')
    op.drop_index('ix_webhook_deliveries_webhook_id', table_name='webhook_deliveries')
    op.drop_table('webhook_deliveries')

    # Drop webhooks
    op.drop_index('ix_webhooks_workspace_status', table_name='webhooks')
    op.drop_index('ix_webhooks_status', table_name='webhooks')
    op.drop_index('ix_webhooks_workspace_id', table_name='webhooks')
    op.drop_table('webhooks')

    # Drop api_keys
    op.drop_index('ix_api_keys_workspace_status', table_name='api_keys')
    op.drop_index('ix_api_keys_status', table_name='api_keys')
    op.drop_index('ix_api_keys_key_hash', table_name='api_keys')
    op.drop_index('ix_api_keys_prefix', table_name='api_keys')
    op.drop_index('ix_api_keys_workspace_id', table_name='api_keys')
    op.drop_table('api_keys')
