"""Produtos normalizados e apelidos (descrições de cupom) ligados a eles.

Revisão: 0002
Anterior: 0001

Só a ESTRUTURA muda aqui. Ligar os itens já existentes aos produtos é feito pelo
comando `compras produtos vincular`, que usa as regras de normalização do código.
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "produtos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("chave", sa.String(200), nullable=False),
        sa.Column("categoria", sa.String(30), nullable=False),
        sa.Column("tamanho", sa.Numeric(12, 3), nullable=True),
        sa.Column("unidade_tamanho", sa.String(5), nullable=True),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("chave"),
    )
    op.create_table(
        "apelidos_produto",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("descricao", sa.String(300), nullable=False),
        sa.Column("produto_id", sa.Integer(), sa.ForeignKey("produtos.id"), nullable=False),
        sa.UniqueConstraint("descricao"),
    )
    op.create_index("ix_apelidos_produto_produto_id", "apelidos_produto", ["produto_id"])

    with op.batch_alter_table("itens_compra") as tabela:
        tabela.add_column(sa.Column("produto_id", sa.Integer(), nullable=True))
        tabela.create_foreign_key("fk_itens_compra_produto", "produtos", ["produto_id"], ["id"])
        tabela.create_index("ix_itens_compra_produto_id", ["produto_id"])


def downgrade() -> None:
    with op.batch_alter_table("itens_compra") as tabela:
        tabela.drop_index("ix_itens_compra_produto_id")
        tabela.drop_constraint("fk_itens_compra_produto", type_="foreignkey")
        tabela.drop_column("produto_id")
    op.drop_index("ix_apelidos_produto_produto_id", "apelidos_produto")
    op.drop_table("apelidos_produto")
    op.drop_table("produtos")
