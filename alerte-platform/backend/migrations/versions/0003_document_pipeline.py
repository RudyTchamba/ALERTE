"""document_pipeline : stockage par périmètre, états de traitement détaillés, historique, date des embeddings

Additive (aucune suppression) : les anciennes lignes gardent leur `status` ; `processing_state` en est déduit.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-25 20:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('knowledge_base', schema=None) as b:
        b.add_column(sa.Column('scope_kind', sa.String(length=16), nullable=False, server_default='country'))
    with op.batch_alter_table('document_version', schema=None) as b:
        b.add_column(sa.Column('storage_path', sa.String(length=600), nullable=True))
        b.add_column(sa.Column('migration_filename', sa.String(length=300), nullable=True))
        b.add_column(sa.Column('download_name', sa.String(length=300), nullable=True))
        b.add_column(sa.Column('provenance', sa.JSON(), nullable=True))
        b.add_column(sa.Column('processing_state', sa.String(length=20), nullable=False, server_default='uploaded'))
        b.add_column(sa.Column('processing_error', sa.Text(), nullable=True))
    with op.batch_alter_table('chunk_embedding', schema=None) as b:
        b.add_column(sa.Column('created_at', sa.DateTime(timezone=True), nullable=True))
    op.create_table('document_event',
    sa.Column('id', sa.String(length=26), nullable=False),
    sa.Column('workspace_id', sa.String(length=26), nullable=False),
    sa.Column('kb_id', sa.String(length=26), nullable=False),
    sa.Column('document_id', sa.String(length=26), nullable=False),
    sa.Column('document_version_id', sa.String(length=26), nullable=False),
    sa.Column('state', sa.String(length=20), nullable=False),
    sa.Column('message', sa.String(length=500), nullable=True),
    sa.Column('job_id', sa.String(length=26), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['document_id'], ['document.id'], name=op.f('fk_document_event_document_id_document')),
    sa.ForeignKeyConstraint(['document_version_id'], ['document_version.id'], name=op.f('fk_document_event_document_version_id_document_version')),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], name=op.f('fk_document_event_workspace_id_workspace')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_document_event'))
    )
    with op.batch_alter_table('document_event', schema=None) as b:
        b.create_index(b.f('ix_document_event_document_id'), ['document_id'], unique=False)
        b.create_index(b.f('ix_document_event_kb_id'), ['kb_id'], unique=False)
        b.create_index(b.f('ix_document_event_workspace_id'), ['workspace_id'], unique=False)
        b.create_index('ix_document_event_version', ['document_version_id', 'created_at'], unique=False)
    # rattrapage : l'état détaillé des lignes existantes est déduit de l'ancien état (une version « processing » héritée d'une
    # interruption devient « queued » : elle pourra être relancée)
    op.execute("UPDATE document_version SET processing_state = CASE status WHEN 'ready' THEN 'ready' WHEN 'needs_review' THEN 'needs_review' "
               "WHEN 'failed' THEN 'failed' WHEN 'retired' THEN 'retired' ELSE 'queued' END")


def downgrade() -> None:
    with op.batch_alter_table('document_event', schema=None) as b:
        b.drop_index('ix_document_event_version')
        b.drop_index(b.f('ix_document_event_workspace_id'))
        b.drop_index(b.f('ix_document_event_kb_id'))
        b.drop_index(b.f('ix_document_event_document_id'))
    op.drop_table('document_event')
    with op.batch_alter_table('chunk_embedding', schema=None) as b:
        b.drop_column('created_at')
    with op.batch_alter_table('document_version', schema=None) as b:
        for c in ('processing_error', 'processing_state', 'provenance', 'download_name', 'migration_filename', 'storage_path'):
            b.drop_column(c)
    with op.batch_alter_table('knowledge_base', schema=None) as b:
        b.drop_column('scope_kind')
