"""Ponto de entrada do Alembic: diz qual banco usar e quais tabelas o código espera."""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from compras.banco.modelos import Base
from compras.config import obter_configuracao

config = context.config
if config.config_file_name is not None and config.attributes.get("configurar_log", True):
    fileConfig(config.config_file_name)

# Permite sobrescrever o banco (usado nos testes); senão usa o DATABASE_URL do .env.
URL = config.get_main_option("sqlalchemy.url") or obter_configuracao().database_url
target_metadata = Base.metadata


def rodar_offline() -> None:
    """Gera o SQL sem conectar (alembic upgrade head --sql)."""
    context.configure(url=URL, target_metadata=target_metadata, literal_binds=True,
                      render_as_batch=URL.startswith("sqlite"))
    with context.begin_transaction():
        context.run_migrations()


def rodar_online() -> None:
    motor = create_engine(URL)
    with motor.connect() as conexao:
        # render_as_batch: o SQLite não suporta ALTER TABLE completo; o Alembic contorna.
        context.configure(connection=conexao, target_metadata=target_metadata,
                          render_as_batch=URL.startswith("sqlite"))
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    rodar_offline()
else:
    rodar_online()
