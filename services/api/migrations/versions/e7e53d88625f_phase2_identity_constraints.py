"""phase2_identity_constraints

Add unique constraints for:
- MerchantUser(merchant_id, user_id) — prevent duplicate memberships
- Product(product_id, merchant_id) — prevent duplicate products
- WebhookEvent(provider, provider_event_id) — prevent duplicate webhook processing

Add FK relationships and indexes on Transaction:
- buyer_id → users.user_id
- merchant_id → merchants.merchant_id

Revision ID: e7e53d88625f
Revises: 057223d89cd2
Create Date: 2026-09-01 22:45:43.283417
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'e7e53d88625f'
down_revision: str | Sequence[str] | None = '057223d89cd2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()

    if conn.dialect.name == 'sqlite':
        with op.batch_alter_table('merchant_users') as batch_op:
            batch_op.create_unique_constraint('uq_merchant_user', ['merchant_id', 'user_id'])
        with op.batch_alter_table('products') as batch_op:
            batch_op.create_unique_constraint('uq_product_merchant', ['product_id', 'merchant_id'])
        with op.batch_alter_table('webhook_events') as batch_op:
            batch_op.create_unique_constraint('uq_webhook_provider_event', ['provider', 'provider_event_id'])
    else:
        # Unique constraints
        op.create_unique_constraint('uq_merchant_user', 'merchant_users', ['merchant_id', 'user_id'])
        op.create_unique_constraint('uq_product_merchant', 'products', ['product_id', 'merchant_id'])
        op.create_unique_constraint('uq_webhook_provider_event', 'webhook_events', ['provider', 'provider_event_id'])

    # buyer_id column on transactions — may already exist from Phase 1 code change;
    # use batch_alter_table for SQLite compatibility.
    inspector = sa.inspect(conn)
    existing_cols = {c['name'] for c in inspector.get_columns('transactions')}

    if 'buyer_id' not in existing_cols:
        op.add_column('transactions', sa.Column('buyer_id', sa.String(), nullable=True))

    # Indexes (safe to create even if column existed)
    existing_indexes = {idx['name'] for idx in inspector.get_indexes('transactions')}
    if 'ix_transactions_buyer_id' not in existing_indexes:
        op.create_index('ix_transactions_buyer_id', 'transactions', ['buyer_id'], unique=False)
    if 'ix_transactions_merchant_id' not in existing_indexes:
        op.create_index('ix_transactions_merchant_id', 'transactions', ['merchant_id'], unique=False)

    # FKs — SQLite doesn't support ALTER TABLE ADD FOREIGN KEY, so skip on SQLite.
    # These will apply correctly on PostgreSQL.
    if conn.dialect.name != 'sqlite':
        op.create_foreign_key(
            'fk_transactions_buyer', 'transactions', 'users',
            ['buyer_id'], ['user_id'],
        )
        op.create_foreign_key(
            'fk_transactions_merchant', 'transactions', 'merchants',
            ['merchant_id'], ['merchant_id'],
        )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    if conn.dialect.name != 'sqlite':
        op.drop_constraint('fk_transactions_merchant', 'transactions', type_='foreignkey')
        op.drop_constraint('fk_transactions_buyer', 'transactions', type_='foreignkey')

    op.drop_index('ix_transactions_merchant_id', table_name='transactions')
    op.drop_index('ix_transactions_buyer_id', table_name='transactions')
    op.drop_column('transactions', 'buyer_id')
    op.drop_constraint('uq_webhook_provider_event', 'webhook_events', type_='unique')
    op.drop_constraint('uq_product_merchant', 'products', type_='unique')
    op.drop_constraint('uq_merchant_user', 'merchant_users', type_='unique')
