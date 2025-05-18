"""Add run table and link to responses table

Revision ID: 97f07a01f4c9
Revises: 
Create Date: 2025-05-18 13:25:38.957842

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '97f07a01f4c9'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # 1. Create the 'run' table
    op.create_table(
        'run',
        sa.Column('run_id', sa.Integer(), primary_key=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True)
    )

    # 2. Add 'run_id' to 'response' table as nullable
    with op.batch_alter_table('response', schema=None) as batch_op:
        batch_op.add_column(sa.Column('run_id', sa.Integer(), nullable=True))

    # 3. Insert a default run for orphaned resposnes - so can then later make it not null
    conn = op.get_bind()
    conn.execute(
        sa.text("INSERT INTO run (description, created_at) VALUES ('[AUTO] Default for orphaned responses', CURRENT_TIMESTAMP)")
    )
    default_run_id = conn.execute(
        sa.text("SELECT run_id FROM run WHERE description='[AUTO] Default for orphaned responses'")
    ).scalar()

    # 4. Update all existing responses to use the default run
    conn.execute(
        sa.text("UPDATE response SET run_id = :default_run_id WHERE run_id IS NULL"),
        {"default_run_id": default_run_id}
    )

    # 5. Alter 'run_id' to be NOT NULL and add FK with RESTRICT
    with op.batch_alter_table('response', schema=None) as batch_op:
        batch_op.alter_column('run_id', existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key(
            'fk_response_run_id', 'run', ['run_id'], ['run_id'], ondelete='RESTRICT'
        )

def downgrade():
    with op.batch_alter_table('response', schema=None) as batch_op:
        batch_op.drop_constraint('fk_response_run_id', type_='foreignkey')
        batch_op.alter_column('run_id', existing_type=sa.Integer(), nullable=True)
        batch_op.drop_column('run_id')

    op.drop_table('run')