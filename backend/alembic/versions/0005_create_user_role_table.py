"""Create user_role table and update is_active default

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-27 09:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create user_role association table
    op.create_table(
        'user_role',
        sa.Column('user_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True, nullable=False),
        sa.Column('role_id', sa.String(length=32), sa.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True, nullable=False),
    )

    # 2. Migrate existing role_id data from users -> user_role
    op.execute("""
        INSERT INTO user_role (user_id, role_id)
        SELECT id, role_id FROM users
        WHERE role_id IS NOT NULL
    """)

    # 3. Change default of is_active to false (new registrations must wait for admin approval)
    op.alter_column('users', 'is_active',
                    existing_type=sa.Boolean(),
                    server_default='false',
                    existing_nullable=False)

    # 4. Keep admin account active (admin was already active, update via data migration)
    op.execute("""
        UPDATE users SET is_active = true
        WHERE username = 'admin'
    """)

    # 5. Drop the old role_id column from users
    op.drop_column('users', 'role_id')


def downgrade() -> None:
    # Re-add role_id column
    op.add_column('users', sa.Column('role_id', sa.String(length=32), nullable=True))

    # Restore data from user_role
    op.execute("""
        UPDATE users u
        SET role_id = ur.role_id
        FROM user_role ur
        WHERE u.id = ur.user_id
    """)

    # Make role_id non-nullable again
    op.alter_column('users', 'role_id', existing_type=sa.String(length=32), nullable=False)
    op.create_foreign_key(None, 'users', 'roles', ['role_id'], ['id'])

    # Restore default is_active to true
    op.alter_column('users', 'is_active',
                    existing_type=sa.Boolean(),
                    server_default='true',
                    existing_nullable=False)

    # Drop user_role table
    op.drop_table('user_role')
