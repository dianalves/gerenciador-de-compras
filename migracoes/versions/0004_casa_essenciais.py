"""Cadastro da casa e itens essenciais (para prever quando cada um vai acabar).

Revisão: 0004
Anterior: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "casa",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("adultos", sa.Integer(), nullable=False),
        sa.Column("criancas", sa.Integer(), nullable=False),
        sa.Column("pets", sa.Integer(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "essenciais",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(60), nullable=False),
        sa.Column("palavras", sa.String(200), nullable=False),
        sa.Column("excluir", sa.String(200), nullable=False),
        sa.Column("unidade", sa.String(5), nullable=False),
        sa.Column("consumo_pessoa_mes", sa.Numeric(10, 3), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("nome"),
    )


def downgrade() -> None:
    op.drop_table("essenciais")
    op.drop_table("casa")
