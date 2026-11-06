from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from compras.config import obter_configuracao

motor = create_engine(obter_configuracao().database_url, future=True)
Sessao = sessionmaker(bind=motor, expire_on_commit=False)


def criar_tabelas() -> None:
    from compras.banco.modelos import Base

    Base.metadata.create_all(motor)
