from typing import Iterator, Optional

from sqlalchemy.orm import Session

from compras.banco.conexao import Sessao
from compras.visao.base import ProvedorVisao
from compras.visao.fabrica import obter_provedor


def obter_sessao() -> Iterator[Session]:
    with Sessao() as sessao:
        yield sessao


def obter_modelo(usar_modelo: bool = True,
                 provedor: Optional[str] = None) -> Optional[ProvedorVisao]:
    """Modelo usado só para categorias de produtos desconhecidos e plano B do HTML."""
    if not usar_modelo:
        return None
    try:
        return obter_provedor(provedor)
    except Exception:  # SDK não instalado, provedor inválido...
        return None
