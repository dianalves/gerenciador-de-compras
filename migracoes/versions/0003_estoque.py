"""Estoque da casa: movimentos de entrada (compras) e saída (consumo).

Revisão: 0003
Anterior: 0002

O estoque inicial (itens da compra mais recente) é criado pelo comando
`compras estoque iniciar`, não aqui.
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "movimentos_estoque",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("produto_id", sa.Integer(), sa.ForeignKey("produtos.id"), nullable=False),
        sa.Column("quantidade", sa.Numeric(12, 3), nullable=False),
        sa.Column("unidade", sa.String(10), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("compra_id", sa.Integer(),
                  sa.ForeignKey("compras.id", ondelete="CASCADE"), nullable=True),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_movimentos_estoque_produto_id", "movimentos_estoque", ["produto_id"])


def downgrade() -> None:
    op.drop_index("ix_movimentos_estoque_produto_id", "movimentos_estoque")
    op.drop_table("movimentos_estoque")
