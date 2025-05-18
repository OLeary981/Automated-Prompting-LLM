"""Add run table and link to responses table

Revision ID: 97f07a01f4c9
Revises: 
Create Date: 2025-05-18 13:25:38.957842

"""
from alembic import op
import sqlalchemy as sa

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '97f07a01f4c9'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create the 'run' table
    op.create_table(
        'run',
        sa.Column('run_id', sa.Integer(), primary_key=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True)
    )

    # Add 'run_id' to 'response' table and link it to 'run'
    with op.batch_alter_table('response', schema=None) as batch_op:
        batch_op.add_column(sa.Column('run_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_response_run_id', 'run', ['run_id'], ['run_id'])


def downgrade():
    with op.batch_alter_table('response', schema=None) as batch_op:
        batch_op.drop_constraint('fk_response_run_id', type_='foreignkey')
        batch_op.drop_column('run_id')

    op.drop_table('run')