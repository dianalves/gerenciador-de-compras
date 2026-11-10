"""Estrutura inicial: estabelecimentos, compras e itens (como já existia antes do Alembic).

Revisão: 0001
Anterior: nenhuma
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "estabelecimentos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("cnpj", sa.String(14), nullable=True),
        sa.UniqueConstraint("cnpj"),
    )
    op.create_table(
        "compras",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("estabelecimento_id", sa.Integer(),
                  sa.ForeignKey("estabelecimentos.id"), nullable=False),
        sa.Column("chave_acesso", sa.String(44), nullable=True),
        sa.Column("data_emissao", sa.DateTime(), nullable=True),
        sa.Column("valor_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("desconto", sa.Numeric(12, 2), nullable=False),
        sa.Column("economia", sa.Numeric(12, 2), nullable=True),
        sa.Column("forma_pagamento", sa.String(50), nullable=True),
        sa.Column("origem", sa.String(20), nullable=False),
        sa.Column("provedor_visao", sa.String(20), nullable=True),
        sa.Column("imagem", sa.String(500), nullable=True),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("chave_acesso"),
    )
    op.create_table(
        "itens_compra",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("compra_id", sa.Integer(), sa.ForeignKey("compras.id"), nullable=False),
        sa.Column("codigo", sa.String(50), nullable=True),
        sa.Column("descricao", sa.String(300), nullable=False),
        sa.Column("quantidade", sa.Numeric(12, 3), nullable=False),
        sa.Column("unidade", sa.String(10), nullable=False),
        sa.Column("valor_unitario", sa.Numeric(12, 2), nullable=False),
        sa.Column("valor_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("categoria", sa.String(30), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("itens_compra")
    op.drop_table("compras")
    op.drop_table("estabelecimentos")
