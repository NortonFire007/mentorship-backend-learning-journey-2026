"""init_users_subscriptions

Revision ID: 001_init_users_subscriptions
Revises: 
Create Date: 2026-04-01 12:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_init_users_subscriptions'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # 1. Create Enums explicitly
    currency_enum = postgresql.ENUM('EUR', 'USD', 'UAH', name='currency_enum')
    currency_enum.create(op.get_bind())
    
    travel_type_enum = postgresql.ENUM('flight', 'hotel', 'package', name='travel_type_enum')
    travel_type_enum.create(op.get_bind())

    # 2. Create 'users' table
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('surname', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('telegram_id', sa.String(length=100), nullable=True),
        sa.Column('preferred_currency', postgresql.ENUM('EUR', 'USD', 'UAH', name='currency_enum', create_type=False), server_default='USD', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 3. Create 'subscriptions' table
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('origin', sa.String(length=255), nullable=True),
        sa.Column('destination', sa.String(length=255), nullable=False),
        sa.Column('travel_type', postgresql.ENUM('flight', 'hotel', 'package', name='travel_type_enum', create_type=False), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('duration_days', sa.Integer(), nullable=True),
        sa.Column('max_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', postgresql.ENUM('EUR', 'USD', 'UAH', name='currency_enum', create_type=False), server_default='USD', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_subscriptions_user_id'), 'subscriptions', ['user_id'], unique=False)

def downgrade():
    # 1. Drop tables
    op.drop_index(op.f('ix_subscriptions_user_id'), table_name='subscriptions')
    op.drop_table('subscriptions')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')

    # 2. Drop Enums
    currency_enum = postgresql.ENUM('EUR', 'USD', 'UAH', name='currency_enum')
    currency_enum.drop(op.get_bind())
    
    travel_type_enum = postgresql.ENUM('flight', 'hotel', 'package', name='travel_type_enum')
    travel_type_enum.drop(op.get_bind())