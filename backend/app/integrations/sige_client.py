"""SIGE V2 placeholder. TODO[ADR-integracao-SIGE-V2].

Quando ativar:
- Configurar pyodbc com SQL Server (SATLTESTE)
- Implementar fetch_peca_by_sku(sku) → dict
- Implementar baixa_estoque_atomica(sku, qtd, os_id) com transação + rollback + DLQ
- Cache Redis ml:peca:{codigo} TTL 48h pra preço mercado
"""
from typing import Optional


def fetch_peca_by_sku(sku: str) -> Optional[dict]:
    return None


def calcular_economia_napel(sku: str, valor_pago: float) -> Optional[float]:
    """V2: cruza preço SIGE (peça Napel) vs preço Mercado Livre → economia em R$."""
    return None
