"""add_tg_chat_id_and_skipped_status

Revision ID: 0e0bfd8b3329
Revises: 40f6d2b30843
Create Date: 2026-07-16 15:57:49.625953

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0e0bfd8b3329'
down_revision: Union[str, Sequence[str], None] = '40f6d2b30843'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add telegram_chat_id (BigInteger, UNIQUE, nullable) to users
    op.add_column('users', sa.Column('telegram_chat_id', sa.BigInteger(), nullable=True))
    op.create_unique_constraint('uq_users_telegram_chat_id', 'users', ['telegram_chat_id'])
    
    # 2. Drop telegram_id from users
    op.drop_column('users', 'telegram_id')
    
    # 3. Add 'skipped' value to alert_status_enum (check if it exists first for idempotency)
    # Postgres doesn't allow altering enums within a transaction block if the new value is used immediately,
    # but since Postgres 12+ it's allowed if not used. Checking before adding avoids DuplicateObjectError.
    connection = op.get_bind()
    has_skipped = connection.execute(sa.text(
        "SELECT 1 FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid "
        "WHERE t.typname = 'alert_status_enum' AND e.enumlabel = 'skipped'"
    )).scalar()
    
    if not has_skipped:
        op.execute("ALTER TYPE alert_status_enum ADD VALUE 'skipped'")


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Drop telegram_chat_id unique constraint and column
    op.drop_constraint('uq_users_telegram_chat_id', 'users', type_='unique')
    op.drop_column('users', 'telegram_chat_id')
    
    # 2. Add telegram_id back to users
    op.add_column('users', sa.Column('telegram_id', sa.String(length=100), nullable=True))
    
    # Note: Removing an enum value is not supported by PostgreSQL ALTER TYPE.
    # Leaving the 'skipped' value in the enum type is safe and has no side effects.
    pass
