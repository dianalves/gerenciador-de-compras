"""As migrações têm que produzir exatamente as tabelas que os modelos esperam."""
import pytest

pytest.importorskip("alembic")

from sqlalchemy import create_engine, inspect  # noqa: E402

from compras.banco.migracoes import atualizar_banco  # noqa: E402
from compras.banco.modelos import Base  # noqa: E402


def test_migracoes_batem_com_os_modelos(tmp_path):
    url = f"sqlite:///{tmp_path / 'teste.db'}"
    atualizar_banco(url)

    inspetor = inspect(create_engine(url))
    for tabela in Base.metadata.sorted_tables:
        no_banco = {c["name"] for c in inspetor.get_columns(tabela.name)}
        nos_modelos = {c.name for c in tabela.columns}
        assert no_banco == nos_modelos, tabela.name


def test_banco_antigo_e_marcado_sem_perder_dados(tmp_path):
    """Simula o seu banco: criado com create_all antes do Alembic, já com dados."""
    from alembic import command

    from compras.banco.migracoes import _configuracao

    url = f"sqlite:///{tmp_path / 'antigo.db'}"
    motor = create_engine(url)
    # recria a estrutura da época (revisão inicial) e apaga o controle de versão,
    # como era o banco antes do Alembic
    command.upgrade(_configuracao(url), "0001")
    with motor.begin() as c:
        c.exec_driver_sql("drop table alembic_version")
    with motor.begin() as c:
        c.exec_driver_sql("insert into estabelecimentos (nome) values ('MERCADO X')")

    assert "marcado" in atualizar_banco(url)
    with motor.connect() as c:
        assert c.exec_driver_sql("select nome from estabelecimentos").scalar() == "MERCADO X"
    assert "alembic_version" in inspect(motor).get_table_names()
