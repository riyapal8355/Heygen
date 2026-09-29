"""Jobs and async task pipeline domain tables: jobs, job_events, idempotency index

Revision ID: 0005_jobs_task_pipeline
Revises: 0004_creative_library
Create Date: 2026-09-12 15:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic (must be <= 32 chars).
revision: str = '0005_jobs_task_pipeline'
down_revision: Union[str, None] = '0004_creative_library'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create jobs table
    op.create_table(
        'jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE', name='fk_jobs_workspace_id'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT', name='fk_jobs_created_by'), nullable=False),
        sa.Column('job_type', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='queued', nullable=False),
        sa.Column('priority', sa.Integer(), server_default='10', nullable=False),
        sa.Column('idempotency_key', sa.String(length=255), nullable=True),
        sa.Column('progress_percent', sa.Integer(), server_default='0', nullable=False),
        sa.Column('stage', sa.String(length=64), nullable=True),
        sa.Column('stage_message', sa.String(length=512), nullable=True),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('celery_task_id', sa.String(length=255), nullable=True),
        sa.Column('retry_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('max_retries', sa.Integer(), server_default='3', nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_jobs_workspace_id', 'jobs', ['workspace_id'])
    op.create_index('ix_jobs_created_by', 'jobs', ['created_by'])
    op.create_index('ix_jobs_job_type', 'jobs', ['job_type'])
    op.create_index('ix_jobs_status', 'jobs', ['status'])
    op.create_index('ix_jobs_celery_task_id', 'jobs', ['celery_task_id'])
    op.create_index('ix_jobs_workspace_status', 'jobs', ['workspace_id', 'status'])
    op.create_index('ix_jobs_workspace_type', 'jobs', ['workspace_id', 'job_type'])
    op.create_index('ix_jobs_created_at', 'jobs', ['created_at'])

    # Partial unique index for active job idempotency per workspace
    op.create_index(
        'uq_jobs_workspace_idempotency',
        'jobs',
        ['workspace_id', 'idempotency_key'],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL AND status NOT IN ('failed', 'cancelled')"),
    )

    # 2. Create job_events table
    op.create_table(
        'job_events',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('jobs.id', ondelete='CASCADE', name='fk_job_events_job_id'), nullable=False),
        sa.Column('event_type', sa.String(length=32), server_default='progress_update', nullable=False),
        sa.Column('from_status', sa.String(length=32), nullable=True),
        sa.Column('to_status', sa.String(length=32), nullable=True),
        sa.Column('progress_percent', sa.Integer(), nullable=True),
        sa.Column('stage', sa.String(length=64), nullable=True),
        sa.Column('message', sa.String(length=512), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_job_events_job_id', 'job_events', ['job_id'])
    op.create_index('ix_job_events_job_created', 'job_events', ['job_id', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_job_events_job_created', table_name='job_events')
    op.drop_index('ix_job_events_job_id', table_name='job_events')
    op.drop_table('job_events')

    op.drop_index('uq_jobs_workspace_idempotency', table_name='jobs')
    op.drop_index('ix_jobs_created_at', table_name='jobs')
    op.drop_index('ix_jobs_workspace_type', table_name='jobs')
    op.drop_index('ix_jobs_workspace_status', table_name='jobs')
    op.drop_index('ix_jobs_celery_task_id', table_name='jobs')
    op.drop_index('ix_jobs_status', table_name='jobs')
    op.drop_index('ix_jobs_job_type', table_name='jobs')
    op.drop_index('ix_jobs_created_by', table_name='jobs')
    op.drop_index('ix_jobs_workspace_id', table_name='jobs')
    op.drop_table('jobs')
