"""seed_user_groups

Revision ID: d2433b3bc450
Revises: 075e386d6de6
Create Date: 2026-05-31 15:24:39.678974

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import column, table

# revision identifiers, used by Alembic.
revision: str = 'd2433b3bc450'
down_revision: Union[str, Sequence[str], None] = '075e386d6de6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    user_groups_table = table(
        'user_groups',
        column('name', sa.String)
    )

    op.bulk_insert(
        user_groups_table,
        [
            {'name': 'user'},
            {'name': 'moderator'},
            {'name': 'admin'}
        ]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DELETE FROM user_groups WHERE name IN ('user', 'moderator', 'admin')")
