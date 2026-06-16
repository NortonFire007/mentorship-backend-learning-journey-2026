"""alter_users_table

Revision ID: 5ff1fb08022f
Revises: ca5e492b3444
Create Date: 2026-06-11 17:44:18.034577

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5ff1fb08022f'
down_revision: Union[str, Sequence[str], None] = 'ca5e492b3444'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('password_hash', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('is_verified', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('users', sa.Column('auth_provider', sa.String(length=50), server_default='local', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'auth_provider')
    op.drop_column('users', 'is_verified')
    op.drop_column('users', 'password_hash')
