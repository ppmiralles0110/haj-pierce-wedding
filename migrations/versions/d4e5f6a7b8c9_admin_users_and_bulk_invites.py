"""admin_users table, invite email column, drop unused guest meal/plus-one fields

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-29

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade():
    # --- admin_users table (portal-granted admin access) ---
    op.create_table(
        'admin_users',
        sa.Column('id',         sa.Integer(),               nullable=False),
        sa.Column('email',      sa.String(length=255),      nullable=False,
                  comment='Email address granted admin access (lowercase)'),
        sa.Column('granted_by', sa.String(length=255),      nullable=True,
                  comment='Email of the admin who granted this access'),
        sa.Column('note',       sa.String(length=255),      nullable=True,
                  comment="Optional label, e.g. the person's name or role"),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  comment='UTC timestamp the grant was created'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('admin_users', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_admin_users_email'), ['email'], unique=True
        )

    # --- optional email on invite codes (populated by bulk import) ---
    with op.batch_alter_table('invite_codes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email', sa.String(length=255), nullable=True))
        batch_op.create_index(
            batch_op.f('ix_invite_codes_email'), ['email'], unique=False
        )

    # --- drop guest fields that are no longer collected ---
    with op.batch_alter_table('guests', schema=None) as batch_op:
        batch_op.drop_column('meal_preference')
        batch_op.drop_column('plus_one')
        batch_op.drop_column('plus_one_name')

    # The enum type lingers on PostgreSQL after its only column is dropped
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        sa.Enum(name='meal_pref_enum').drop(bind, checkfirst=True)


def downgrade():
    bind = op.get_bind()
    meal_enum = sa.Enum(
        'chicken', 'fish', 'vegetarian', 'vegan', name='meal_pref_enum'
    )
    if bind.dialect.name == 'postgresql':
        meal_enum.create(bind, checkfirst=True)

    with op.batch_alter_table('guests', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'meal_preference', meal_enum, nullable=True,
            comment='Meal preference: chicken | fish | vegetarian | vegan',
        ))
        batch_op.add_column(sa.Column(
            'plus_one', sa.Boolean(), nullable=False, server_default=sa.false(),
            comment='True if guest is bringing a plus-one',
        ))
        batch_op.add_column(sa.Column(
            'plus_one_name', sa.String(length=255), nullable=True,
            comment='Full name of the plus-one guest',
        ))

    with op.batch_alter_table('invite_codes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_invite_codes_email'))
        batch_op.drop_column('email')

    with op.batch_alter_table('admin_users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_admin_users_email'))

    op.drop_table('admin_users')
