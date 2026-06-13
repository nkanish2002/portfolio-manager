"""add_cusip_column_to_assets

Revision ID: 18ab48ee7c87
Revises: 30b840d15fd1
Create Date: 2026-06-09 21:18:33.496365

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '18ab48ee7c87'
down_revision: Union[str, Sequence[str], None] = '30b840d15fd1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('assets') as batch_op:
        batch_op.add_column(sa.Column('cusip', sa.String(length=12), nullable=True, index=True))

    # Update existing assets with a placeholder CUSIP if symbol is set
    # This is a placeholder - in production you would populate actual CUSIPs
    op.execute("UPDATE assets SET cusip = symbol || '_placeholder' WHERE symbol IS NOT NULL AND cusip IS NULL")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('assets') as batch_op:
        batch_op.drop_column('cusip')
