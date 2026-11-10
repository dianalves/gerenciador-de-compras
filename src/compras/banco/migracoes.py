"""Aplica as migrações do Alembic a partir do código (usado pelo `compras iniciar-banco`)."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, inspect

RAIZ = Path(__file__).resolve().parents[3]  # src/compras/banco/ -> raiz do projeto
REVISAO_INICIAL = "0001"


def _configuracao(url: Optional[str] = None):
    from alembic.config import Config

    cfg = Config(str(RAIZ / "alembic.ini"))
    cfg.set_main_option("script_location", str(RAIZ / "migracoes"))
    if url:
        cfg.set_main_option("sqlalchemy.url", url)
    cfg.attributes["configurar_log"] = False
    return cfg


def atualizar_banco(url: Optional[str] = None) -> str:
    """Leva o banco até a última migração. Devolve o que foi feito, para mostrar ao usuário.

    Banco criado antes do Alembic (tabelas existem, sem controle de versão): é marcado como
    estando na revisão inicial e só as migrações novas rodam. Nenhum dado é apagado.
    """
    from alembic import command

    from compras.config import obter_configuracao

    url = url or obter_configuracao().database_url
    cfg = _configuracao(url)
    tabelas = set(inspect(create_engine(url)).get_table_names())

    aviso = ""
    if "compras" in tabelas and "alembic_version" not in tabelas:
        command.stamp(cfg, REVISAO_INICIAL)
        aviso = "Banco existente marcado como versão inicial (dados preservados). "
    command.upgrade(cfg, "head")
    return aviso + "Banco atualizado até a última migração."


def nova_migracao(mensagem: str) -> None:
    """Gera um arquivo de migração comparando os modelos com o banco atual."""
    from alembic import command

    command.revision(_configuracao(), message=mensagem, autogenerate=True)
