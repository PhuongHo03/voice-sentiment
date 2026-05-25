"""Initial schema

Revision ID: 0001
Revises: None
Create Date: 2026-05-25 15:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create analysis_jobs table
    op.create_table(
        'analysis_jobs',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('input_type', sa.String(length=16), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False, server_default='pending'),
        sa.Column('audio_object_key', sa.String(length=512), nullable=True),
        sa.Column('submitted_text', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    )
    
    # 2. Create analysis_results table
    op.create_table(
        'analysis_results',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('job_id', UUID(as_uuid=False), sa.ForeignKey('analysis_jobs.id'), unique=True, nullable=False),
        sa.Column('transcript_json', JSONB(), nullable=False),
        sa.Column('summary_json', JSONB(), nullable=False),
        sa.Column('sentiment', sa.String(length=32), nullable=False),
        sa.Column('sentiment_reason', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    )


def downgrade() -> None:
    op.drop_table('analysis_results')
    op.drop_table('analysis_jobs')
