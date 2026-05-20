"""Máquina de estados OS + validação NF/foto pra encerrar."""
from typing import Dict, List, Set, Tuple

from .models import OrdemServico, StatusOsEnum, TipoAnexoEnum

TRANSICOES_VALIDAS: Dict[StatusOsEnum, Set[StatusOsEnum]] = {
    StatusOsEnum.rascunho:           {StatusOsEnum.aberta, StatusOsEnum.cancelada},
    StatusOsEnum.aberta:             {StatusOsEnum.aguardando_anexos, StatusOsEnum.em_execucao, StatusOsEnum.cancelada},
    StatusOsEnum.aguardando_anexos:  {StatusOsEnum.pronta_execucao, StatusOsEnum.em_execucao, StatusOsEnum.cancelada},
    StatusOsEnum.pronta_execucao:    {StatusOsEnum.em_execucao, StatusOsEnum.cancelada},
    StatusOsEnum.em_execucao:        {StatusOsEnum.encerrada, StatusOsEnum.cancelada},
    StatusOsEnum.encerrada:          {StatusOsEnum.aberta},        # admin reabre
    StatusOsEnum.cancelada:          set(),
}


def pode_transicao(de: StatusOsEnum, para: StatusOsEnum) -> bool:
    return para in TRANSICOES_VALIDAS.get(de, set())


def tem_nf(os: OrdemServico) -> bool:
    return any(a.tipo == TipoAnexoEnum.nf for a in os.anexos)


def tem_foto(os: OrdemServico) -> bool:
    return any(
        a.tipo in (TipoAnexoEnum.foto_hodometro, TipoAnexoEnum.foto_problema)
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
