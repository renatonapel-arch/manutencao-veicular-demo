"""Mock Evolution WhatsApp — toast preview no MVP.

TODO[ADR-evolution-whatsapp]: substituir mock por integração real Evolution sandbox
quando OWNERS.md for assinado (Cesar infra + Renato worker + PM templates).
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from ..config import settings
from ..models import AlertaHistory, OrdemServico, VeiculoSnapshot

log = logging.getLogger("manutencao.evolution")


def render_template(
    tipo: str,
    template: Optional[str],
    os: Optional[OrdemServico] = None,
    veiculo: Optional[VeiculoSnapshot] = None,
) -> str:
    nome_dest = "Hudson"  # placeholder — real seria pelo destinatario_user_id
    placa = veiculo.placa if veiculo else (os.veiculo.placa if os and os.veiculo else "?")
    modelo = veiculo.modelo if veiculo else (os.veiculo.modelo if os and os.veiculo else "?")
    valor = float(os.valor_total) if os else 0.0
    of = os.oficina.nome if os and os.oficina else "—"
    descr = os.descricao_problema if os else "—"
    link = f"https://manutencao.demos.napel.com.br/os/{os.id}" if os else "https://manutencao.demos.napel.com.br"

    if tipo == "preventiva_proxima":
        return (
            f"⚠️ {nome_dest}, manutenção preventiva próxima:\n\n"
            f"🚗 {placa} ({modelo})\n"
            f"🔧 {descr}\n\n"
            f"Verificar agendamento.\n{link}\n\n— Clavis Manutenção"
        )
    if tipo == "os_aberta_dias":
        return (
            f"⚠️ {nome_dest}, a OS #{os.id if os else '?'} está aberta há mais de 5 dias:\n\n"
            f"🚗 {placa} ({modelo})\n"
            f"🏪 {of}\n"
            f"💰 R$ {valor:.2f}\n\n"
            f"Verificar conclusão.\n{link}\n\n— Clavis Manutenção"
        )
    if tipo == "custo_fora_padrao":
        return (
            f"⚠️ Custo anômalo na OS #{os.id if os else '?'}:\n\n"
            f"🚗 {placa} ({modelo})\n"
            f"💰 R$ {valor:.2f} (acima da média do modelo)\n\n"
            f"Renegociar com a oficina antes de autorizar.\n{link}\n\n— Clavis Manutenção"
        )
    if tipo == "solicitar_nf":
        return (
            f"Olá, poderia enviar a NF da OS #{os.id if os else '?'} ({placa})?\n\n"
            f"💰 R$ {valor:.2f}\n\n"
            f"Obrigado.\n— Napel · Clavis Manutenção"
        )
    return (
        f"{nome_dest}, atualização da OS #{os.id if os else '?'} — {placa} ({modelo}):\n\n"
        f"🔧 {descr}\n"
        f"🏪 {of}\n"
        f"💰 R$ {valor:.2f}\n\n"
        f"{link}\n\n— Clavis Manutenção"
    )


def dispatch_alerta(alerta: AlertaHistory) -> dict:
    """Mock: registra como 'sent' imediatamente; real entra na fila Redis."""
    if not settings.EVOLUTION_ENABLED:
        alerta.status = "sent"  # mock: simula entrega bem-sucedida
        alerta.sent_at = datetime.utcnow()
        log.info("Evolution MOCK · alerta_id=%s · telefone=%s · mock=true",
                 alerta.id, alerta.telefone)
        return {"sent": False, "mock": True, "preview": alerta.mensagem}
    # TODO[ADR-evolution-whatsapp]: enfileirar em Redis pra worker async
    alerta.status = "pending"
    return {"sent": False, "queued": True}
