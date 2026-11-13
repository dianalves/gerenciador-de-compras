"""Essenciais definidos pelo usuário: produtos escolhidos e tamanho do "pacote".

Revisão: 0005
Anterior: 0004
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "essencial_produtos",
        sa.Column("essencial_id", sa.Integer(),
                  sa.ForeignKey("essenciais.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("produto_id", sa.Integer(),
                  sa.ForeignKey("produtos.id", ondelete="CASCADE"), primary_key=True),
    )
    with op.batch_alter_table("essenciais") as tabela:
        tabela.add_column(sa.Column("quantidade_pacote", sa.Numeric(10, 3), nullable=True))
    # casas que já existem já receberam as sugestões (criadas pela versão anterior)
    with op.batch_alter_table("casa") as tabela:
        tabela.add_column(sa.Column("padroes_criados", sa.Boolean(), nullable=False,
                                    server_default=sa.true()))


def downgrade() -> None:
    with op.batch_alter_table("casa") as tabela:
        tabela.drop_column("padroes_criados")
    with op.batch_alter_table("essenciais") as tabela:
        tabela.drop_column("quantidade_pacote")
    op.drop_table("essencial_produtos")
