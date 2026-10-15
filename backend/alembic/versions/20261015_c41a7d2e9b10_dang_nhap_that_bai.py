"""bang dang_nhap_that_bai (chong do mat khau dung chung giua cac worker)

Revision ID: c41a7d2e9b10
Revises: b82b903feadf
Create Date: 2026-10-15 09:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = 'c41a7d2e9b10'
down_revision = 'b82b903feadf'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'dang_nhap_that_bai',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('ip', sa.String(length=64), nullable=False),
        sa.Column('email_hash', sa.String(length=64), nullable=False),
        sa.Column('luc', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_dang_nhap_that_bai')),
    )
    op.create_index('ix_dnt_ip_luc', 'dang_nhap_that_bai', ['ip', 'luc'])
    op.create_index('ix_dnt_email_luc', 'dang_nhap_that_bai', ['email_hash', 'luc'])


def downgrade() -> None:
    op.drop_index('ix_dnt_email_luc', table_name='dang_nhap_that_bai')
    op.drop_index('ix_dnt_ip_luc', table_name='dang_nhap_that_bai')
    op.drop_table('dang_nhap_that_bai')
