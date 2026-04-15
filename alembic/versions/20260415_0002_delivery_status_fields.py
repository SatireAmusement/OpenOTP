"""delivery status fields

Revision ID: 20260415_0002
Revises: 20260415_0001
Create Date: 2026-04-15 06:30:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260415_0002"
down_revision = "20260415_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("otp_challenges", sa.Column("delivery_status", sa.String(length=32), nullable=True))
    op.add_column("otp_challenges", sa.Column("delivery_error_code", sa.String(length=32), nullable=True))
    op.add_column("otp_challenges", sa.Column("delivery_status_at", sa.DateTime(), nullable=True))
    op.create_index(op.f("ix_otp_challenges_delivery_status"), "otp_challenges", ["delivery_status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_otp_challenges_delivery_status"), table_name="otp_challenges")
    op.drop_column("otp_challenges", "delivery_status_at")
    op.drop_column("otp_challenges", "delivery_error_code")
    op.drop_column("otp_challenges", "delivery_status")
