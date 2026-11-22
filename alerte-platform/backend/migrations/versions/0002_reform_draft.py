"""reform_draft : projets de texte vérifiables rattachés aux lacunes

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-22 21:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('reform_draft',
    sa.Column('id', sa.String(length=26), nullable=False),
    sa.Column('workspace_id', sa.String(length=26), nullable=False),
    sa.Column('gap_id', sa.String(length=26), nullable=False),
    sa.Column('exercise_id', sa.String(length=26), nullable=False),
    sa.Column('content', sa.JSON(), nullable=False),
    sa.Column('anchors', sa.JSON(), nullable=False),
    sa.Column('verified', sa.Boolean(), nullable=False),
    sa.Column('model', sa.String(length=120), nullable=False),
    sa.Column('content_sha256', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['gap_id'], ['gap.id'], name=op.f('fk_reform_draft_gap_id_gap'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_reform_draft'))
    )
    with op.batch_alter_table('reform_draft', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_reform_draft_content_sha256'), ['content_sha256'], unique=True)
        batch_op.create_index(batch_op.f('ix_reform_draft_gap_id'), ['gap_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_reform_draft_workspace_id'), ['workspace_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('reform_draft', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_reform_draft_workspace_id'))
        batch_op.drop_index(batch_op.f('ix_reform_draft_gap_id'))
        batch_op.drop_index(batch_op.f('ix_reform_draft_content_sha256'))
    op.drop_table('reform_draft')
