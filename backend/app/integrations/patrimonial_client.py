"""Mock do Controle Patrimonial. TODO[ADR-contratos-APIs-externas]."""
from datetime import datetime
from typing import List


def fetch_veiculos_patrimonial(filial_id: int) -> List[dict]:
    """Shape esperado quando o módulo real existir.

    Real: GET https://controle-patrimonial.napel.com.br/api/v1/veiculos?filial_id={filial_id}
    """
    return []  # demo seed já popula a tabela; sync real não roda no MVP


def fetch_veiculo_by_placa(placa: str) -> dict | None:
    return None
