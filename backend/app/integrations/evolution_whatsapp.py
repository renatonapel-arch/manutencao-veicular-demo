"""Notificações WhatsApp via notifier central da Napel.

- EVOLUTION_ENABLED=false → toast preview (mock, default seguro)
- EVOLUTION_ENABLED=true  → POST pro notifier (http://195.35.19.31:18200)
  que enfileira e envia via Evolution dentro da janela 06-22 BRT.

Padrão Napel: alertas pontuais/ad-hoc viajam como texto puro. 1 evento = 1 msg.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import httpx

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


def _enviar_via_notifier(telefone: str, mensagem: str, tag: str) -> dict:
    """POST pro notifier central. Ele cuida da janela 22-06 BRT + Evolution."""
    url = f"{settings.NOTIFIER_URL.rstrip('/')}/"
    payload = {
        "to": telefone,
        "text": mensagem,
        "source": "manutencao-veicular-demo",
        "tag": tag,
    }
    try:
        with httpx.Client(timeout=8.0) as c:
            r = c.post(url, json=payload)
            r.raise_for_status()
        log.info("Notifier OK · tag=%s · tel=***%s", tag, telefone[-4:])
        body = r.json() if r.headers.get("content-type","").startswith("application/json") else r.text
        return {"sent": True, "via": "notifier", "response": body}
    except httpx.HTTPError as e:
        log.exception("Notifier falhou (tag=%s): %s", tag, e)
        return {"sent": False, "error": str(e)}


def dispatch_alerta(alerta: AlertaHistory) -> dict:
    """Envia o alerta. Mock se EVOLUTION_ENABLED=false; real via notifier se true."""
    if not settings.EVOLUTION_ENABLED:
        alerta.status = "sent"  # mock
        alerta.sent_at = datetime.utcnow()
        log.info("MOCK · tag=%s", alerta.tipo_alerta)
        return {"sent": False, "mock": True, "preview": alerta.mensagem}

    result = _enviar_via_notifier(
        telefone=alerta.telefone or settings.RENATO_WHATSAPP,
        mensagem=alerta.mensagem or "",
        tag=f"manutencao:{alerta.tipo_alerta}:{alerta.os_id or alerta.veiculo_id or '?'}",
    )
    if result.get("sent"):
        alerta.status = "sent"
        alerta.sent_at = datetime.utcnow()
    else:
        alerta.status = "failed"
        alerta.error_msg = (result.get("error") or "?")[:500]
    return result
