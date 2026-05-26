"""Add agent evaluation

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-26 15:48:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('analysis_results', sa.Column('agent_score', sa.Integer(), nullable=True))
    op.add_column('analysis_results', sa.Column('agent_advice_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('analysis_results', 'agent_advice_json')
    op.drop_column('analysis_results', 'agent_score')
