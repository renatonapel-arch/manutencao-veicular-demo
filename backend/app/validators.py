"""Validações de anexo/item pra encerrar OS.

A máquina de estados vive em service.TRANSICOES_VALIDAS (v3) — este módulo
não duplica mais o mapa de transições.
"""
from typing import List, Tuple

from .models import OrdemServico


def tem_nf(os: OrdemServico) -> bool:
    return any(a.tipo == "nf" for a in os.anexos)


def tem_foto(os: OrdemServico) -> bool:
    return any(
        a.tipo in ("foto_hodometro", "foto_problema", "foto_pneu")
        for a in os.anexos
    )


def pode_encerrar(os: OrdemServico) -> Tuple[bool, List[str]]:
    erros: List[str] = []
    if not tem_foto(os):
        erros.append("Pelo menos 1 foto (hodômetro ou problema)")
    if not tem_nf(os):
        erros.append("NF/comprovante obrigatório")
    if not os.itens:
        erros.append("Pelo menos 1 item lançado")
    return (len(erros) == 0, erros)
