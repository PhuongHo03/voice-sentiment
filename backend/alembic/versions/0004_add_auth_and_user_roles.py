"""Add auth and user roles

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-27 08:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime
from uuid import uuid4

# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, None] = '0003'
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

    # 2. Insert default roles
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

    # 3. Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('username', sa.String(length=128), nullable=False),
        sa.Column('email', sa.String(length=128), nullable=False),
        sa.Column('hashed_password', sa.String(length=256), nullable=False),
        sa.Column('role_id', sa.String(length=32), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )

    # 4. Insert pre-seeded admin user: admin / admin123
    # Bcrypt hash of 'admin123'
    hashed_admin123 = '$2b$12$i7Cqd7dg.FEIVozJdcQ6Ze1TAW80.mz9T0keQAmqVMv94TdMUSv6i'
    admin_uuid = str(uuid4())
    users_table = sa.table(
        'users',
        sa.column('id', postgresql.UUID(as_uuid=False)),
        sa.column('username', sa.String),
        sa.column('email', sa.String),
        sa.column('hashed_password', sa.String),
        sa.column('role_id', sa.String),
        sa.column('is_active', sa.Boolean),
        sa.column('created_at', sa.DateTime)
    )
    op.bulk_insert(
        users_table,
        [
            {
                'id': admin_uuid,
                'username': 'admin',
                'email': 'admin@voice-sentiment.com',
                'hashed_password': hashed_admin123,
                'role_id': 'admin',
                'is_active': True,
                'created_at': datetime.now()
            }
        ]
    )

    # 5. Add owner_id to analysis_jobs
    op.add_column('analysis_jobs', sa.Column('owner_id', postgresql.UUID(as_uuid=False), nullable=True))
    op.create_foreign_key(
        'fk_analysis_jobs_owner_id_users',
        'analysis_jobs', 'users',
        ['owner_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    op.drop_constraint('fk_analysis_jobs_owner_id_users', 'analysis_jobs', type_='foreignkey')
    op.drop_column('analysis_jobs', 'owner_id')
    op.drop_table('users')
    op.drop_table('roles')
