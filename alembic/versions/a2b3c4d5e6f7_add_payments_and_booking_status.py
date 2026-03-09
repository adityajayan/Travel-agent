"""add payments table and booking status columns

Revision ID: a2b3c4d5e6f7
Revises: fce895cfd7a1
Create Date: 2026-03-08 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, Sequence[str], None] = 'fce895cfd7a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create payments table
    op.create_table('payments',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('trip_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('stripe_checkout_session_id', sa.String(), nullable=True),
        sa.Column('stripe_payment_intent_id', sa.String(), nullable=True),
        sa.Column('amount_cents', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(), server_default='usd', nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_payments_trip', 'payments', ['trip_id'])
    op.create_index('ix_payments_stripe_session', 'payments', ['stripe_checkout_session_id'])

    # Add payment_status to trips
    op.add_column('trips', sa.Column('payment_status', sa.String(), server_default='unpaid', nullable=False))

    # Add status and booking_reference to bookings
    op.add_column('bookings', sa.Column('status', sa.String(), server_default='confirmed', nullable=False))
    op.add_column('bookings', sa.Column('booking_reference', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('bookings', 'booking_reference')
    op.drop_column('bookings', 'status')
    op.drop_column('trips', 'payment_status')
    op.drop_index('ix_payments_stripe_session', table_name='payments')
    op.drop_index('ix_payments_trip', table_name='payments')
    op.drop_table('payments')
