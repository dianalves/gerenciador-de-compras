"""Lista de compras: sugestões dos essenciais acabando + itens do usuário.

Revisão: 0006
Anterior: 0005
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lista_compras",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("texto", sa.String(120), nullable=False),
        sa.Column("quantidade", sa.Numeric(10, 3), nullable=True),
        sa.Column("unidade", sa.String(5), nullable=True),
        sa.Column("essencial_id", sa.Integer(),
                  sa.ForeignKey("essenciais.id", ondelete="SET NULL"), nullable=True),
        sa.Column("origem", sa.String(10), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("lista_compras")
