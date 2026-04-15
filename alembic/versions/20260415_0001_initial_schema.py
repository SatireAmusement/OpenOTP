"""initial schema

Revision ID: 20260415_0001
Revises:
Create Date: 2026-04-15 05:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260415_0001"
down_revision = None
branch_labels = None
depends_on = None


otp_status = sa.Enum("pending", "verified", "expired", "blocked", name="otpstatus")


def upgrade() -> None:
    bind = op.get_bind()
    otp_status.create(bind, checkfirst=True)

    op.create_table(
        "otp_challenges",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("phone_number", sa.String(length=32), nullable=False),
        sa.Column("purpose", sa.String(length=64), nullable=False),
        sa.Column("otp_hash", sa.String(length=128), nullable=False),
        sa.Column("otp_salt", sa.String(length=64), nullable=False),
        sa.Column("status", otp_status, nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("resend_count", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("delivery_provider", sa.String(length=32), nullable=True),
        sa.Column("delivery_reference", sa.String(length=128), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("last_sent_at", sa.DateTime(), nullable=False),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_otp_challenges_expires_at"), "otp_challenges", ["expires_at"], unique=False)
    op.create_index(op.f("ix_otp_challenges_phone_number"), "otp_challenges", ["phone_number"], unique=False)
    op.create_index(op.f("ix_otp_challenges_purpose"), "otp_challenges", ["purpose"], unique=False)
    op.create_index(op.f("ix_otp_challenges_status"), "otp_challenges", ["status"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("phone_number", sa.String(length=32), nullable=False),
        sa.Column("purpose", sa.String(length=64), nullable=False),
        sa.Column("challenge_id", sa.String(length=36), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_challenge_id"), "audit_logs", ["challenge_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"], unique=False)
    op.create_index(op.f("ix_audit_logs_event_type"), "audit_logs", ["event_type"], unique=False)
    op.create_index(op.f("ix_audit_logs_ip_address"), "audit_logs", ["ip_address"], unique=False)
    op.create_index(op.f("ix_audit_logs_outcome"), "audit_logs", ["outcome"], unique=False)
    op.create_index(op.f("ix_audit_logs_phone_number"), "audit_logs", ["phone_number"], unique=False)
    op.create_index(op.f("ix_audit_logs_purpose"), "audit_logs", ["purpose"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_purpose"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_phone_number"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_outcome"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_ip_address"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_event_type"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_created_at"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_challenge_id"), table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index(op.f("ix_otp_challenges_status"), table_name="otp_challenges")
    op.drop_index(op.f("ix_otp_challenges_purpose"), table_name="otp_challenges")
    op.drop_index(op.f("ix_otp_challenges_phone_number"), table_name="otp_challenges")
    op.drop_index(op.f("ix_otp_challenges_expires_at"), table_name="otp_challenges")
    op.drop_table("otp_challenges")

    bind = op.get_bind()
    otp_status.drop(bind, checkfirst=True)
