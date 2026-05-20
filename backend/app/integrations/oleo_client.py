"""Mock do app Troca de Óleo. TODO[ADR-contratos-APIs-externas]."""
from typing import List


def fetch_trocas_oleo_veiculo(veiculo_id: int) -> List[dict]:
    """Real: GET https://troca-oleo.demos.napel.com.br/api/v1/historico-oleo/{veiculo_id}"""
    return []  # cache já populado pelo seed
