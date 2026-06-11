"""Consolidated Initial Schema

Revision ID: 0001
Revises: None
Create Date: 2026-05-25 15:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from datetime import datetime
from uuid import uuid4

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create roles table
    op.create_table(
        'roles',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('description', sa.String(length=256), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Seed default roles
    roles_table = sa.table(
        'roles',
        sa.column('id', sa.String),
        sa.column('name', sa.String),
        sa.column('description', sa.String)
    )
    op.bulk_insert(
        roles_table,
        [
            {'id': 'admin', 'name': 'Administrator', 'description': 'System Administrator'},
            {'id': 'employee', 'name': 'Employee', 'description': 'Standard Employee Account'}
        ]
    )

    # 2. Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('username', sa.String(length=128), nullable=False),
        sa.Column('email', sa.String(length=128), nullable=False),
        sa.Column('hashed_password', sa.String(length=256), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )

    # Seed admin user (admin / admin123)
    # Bcrypt hash of 'admin123'
    hashed_admin123 = '$2b$12$i7Cqd7dg.FEIVozJdcQ6Ze1TAW80.mz9T0keQAmqVMv94TdMUSv6i'
    admin_uuid = str(uuid4())
    users_table = sa.table(
        'users',
        sa.column('id', sa.String),
        sa.column('username', sa.String),
        sa.column('email', sa.String),
        sa.column('hashed_password', sa.String),
        sa.column('is_active', sa.Boolean),
        sa.column('created_at', sa.DateTime)
    )
    op.bulk_insert(
        users_table,
        [
            {
                'id': admin_uuid,
                'username': 'admin',
                'email': 'admin@nhattienchung.vn',
                'hashed_password': hashed_admin123,
                'is_active': True,
                'created_at': datetime.now()
            }
        ]
    )

    # 3. Create user_role association table
    op.create_table(
        'user_role',
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True, nullable=False),
        sa.Column('role_id', sa.String(length=32), sa.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True, nullable=False),
    )

    # Seed admin user role relation
    user_role_table = sa.table(
        'user_role',
        sa.column('user_id', sa.String),
        sa.column('role_id', sa.String)
    )
    op.bulk_insert(
        user_role_table,
        [
            {'user_id': admin_uuid, 'role_id': 'admin'}
        ]
    )

    # 4. Create analysis_jobs table
    op.create_table(
        'analysis_jobs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=256), nullable=True),
        sa.Column('input_type', sa.String(length=16), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False, server_default='pending'),
        sa.Column('audio_object_key', sa.String(length=512), nullable=True),
        sa.Column('submitted_text', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('owner_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_heartbeat_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('attempt_count', sa.Integer(), server_default='0', nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 5. Create analysis_results table
    op.create_table(
        'analysis_results',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('job_id', sa.String(length=36), sa.ForeignKey('analysis_jobs.id'), unique=True, nullable=False),
        sa.Column('transcript_json', JSONB(), nullable=False),
        sa.Column('summary_json', JSONB(), nullable=False),
        sa.Column('sentiment', sa.String(length=32), nullable=False),
        sa.Column('sentiment_reason', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('agent_score', sa.Integer(), nullable=True),
        sa.Column('agent_advice_json', JSONB(), nullable=True),
        sa.Column('detailed_summary_json', JSONB(), nullable=True),
        sa.Column('agent_score_breakdown_json', JSONB(), nullable=True),
        sa.Column('quality_notes_json', JSONB(), nullable=True),
        sa.Column('analysis_metadata_json', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('analysis_results')
    op.drop_table('analysis_jobs')
    op.drop_table('user_role')
    op.drop_table('users')
    op.drop_table('roles')
