# Use Flask-Migrate to generate the migration
# Then modify it to add your new fields safely

"""Add provider configuration fields

Revision ID: abc123def456
Revises: previous_migration_id
Create Date: 2023-05-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'abc123def456'
down_revision = 'previous_migration_id'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to the provider table
    op.add_column('provider', sa.Column('module_name', sa.String(128), nullable=True))
    op.add_column('provider', sa.Column('config_json', sa.Text(), nullable=True))
    op.add_column('provider', sa.Column('display_name', sa.String(128), nullable=True))
    op.add_column('provider', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('provider', sa.Column('enabled', sa.Boolean(), nullable=True, default=True))

    # Initialize module names based on provider names
    op.execute("UPDATE provider SET module_name = LOWER(provider_name) || '_provider' WHERE module_name IS NULL")
    op.execute("UPDATE provider SET enabled = TRUE WHERE enabled IS NULL")
    
    # Make module_name not nullable after initializing values
    op.alter_column('provider', 'module_name', nullable=False)


def downgrade():
    op.drop_column('provider', 'module_name')
    op.drop_column('provider', 'config_json')
    op.drop_column('provider', 'display_name')
    op.drop_column('provider', 'description')
    op.drop_column('provider', 'enabled')