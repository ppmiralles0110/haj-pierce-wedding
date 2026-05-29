"""add invite_codes table and guest/code fields to login_logs

Revision ID: c3d4e5f6a7b8
Revises: 9c141af569aa
Create Date: 2026-05-29

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = '9c141af569aa'
branch_labels = None
depends_on = None


def upgrade():
    # --- invite_codes table ---
    op.create_table(
        'invite_codes',
        sa.Column('id',         sa.Integer(),                  nullable=False),
        sa.Column('code',       sa.String(length=8),           nullable=False),
        sa.Column('label',      sa.String(length=200),         nullable=False),
        sa.Column('is_active',  sa.Boolean(),                  nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),    nullable=False),
        sa.Column('use_count',  sa.Integer(),                  nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('invite_codes', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_invite_codes_code'), ['code'], unique=True
        )

    # --- add new columns to login_logs ---
    with op.batch_alter_table('login_logs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('guest_name',   sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('invite_code',  sa.String(length=8),   nullable=True))
        batch_op.add_column(sa.Column('invite_label', sa.String(length=200), nullable=True))


def downgrade():
    with op.batch_alter_table('login_logs', schema=None) as batch_op:
        batch_op.drop_column('invite_label')
        batch_op.drop_column('invite_code')
        batch_op.drop_column('guest_name')

    with op.batch_alter_table('invite_codes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_invite_codes_code'))

    op.drop_table('invite_codes')
