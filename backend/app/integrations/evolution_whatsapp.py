"""Notificações WhatsApp via notifier central da Napel.

- EVOLUTION_ENABLED=false → mock (log preview, não envia)
- EVOLUTION_ENABLED=true  → POST pro notifier (http://195.35.19.31:18200)
  que enfileira e envia via Evolution respeitando janela 22-06 BRT.

Templates limpos: sem emoji, cada evento uma mensagem curta com link direto
pra tela de decisão. Padrão Napel — playbook UI/UX (zero emoji).

Uso principal: notify_os_transition(db, os, evento) chamado no service
após cada db.commit() de transição relevante.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import AlertaHistory, MembroManutencao, OrdemServico, User, VeiculoSnapshot

log = logging.getLogger("manutencao.evolution")

BASE_URL = "https://manutencao.demos.napel.com.br"


# --- Templates (limpo, sem emoji) -----------------------------------------

def _linha_veiculo(os: OrdemServico) -> str:
    v = os.veiculo
    if not v:
        return f"veiculo #{os.veiculo_id}"
    return f"{v.placa} · {v.modelo or ''}".strip(" ·")


def _linha_valor(os: OrdemServico) -> str:
    v = float(os.valor_total or 0)
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _link(os: OrdemServico) -> str:
    return f"{BASE_URL}/os/{os.id}"


def render(evento: str, os: OrdemServico, destinatario: Optional[User] = None) -> str:
    nome = (destinatario.nome.split(" ")[0] if destinatario else "colega")
    v = _linha_veiculo(os)
    valor = _linha_valor(os)
    link = _link(os)
    of = os.oficina.nome if os.oficina else "—"

    if evento == "aberta":
        return (
            f"Nova OS #{os.id} aberta\n"
            f"{v}\n"
            f"Problema: {os.descricao_problema or '—'}\n\n"
            f"Fazer triagem: {link}"
        )

    if evento == "aguardando_aprovacao":
        return (
            f"{nome}, aprovação pendente na OS #{os.id}\n"
            f"{v}\n"
            f"Oficina: {of}\n"
            f"Valor: {valor}\n\n"
            f"Aprovar ou reprovar: {link}"
        )

    if evento == "auto_aprovada":
        return (
            f"OS #{os.id} auto-aprovada ({valor})\n"
            f"{v}\n"
            f"Valor abaixo do teto — segue direto pra execução.\n\n"
            f"Ver: {link}"
        )

    if evento == "aprovada":
        return (
            f"OS #{os.id} aprovada — pode executar\n"
            f"{v}\n"
            f"Oficina: {of}\n"
            f"Valor: {valor}\n\n"
            f"Detalhes: {link}"
        )

    if evento == "reprovada":
        return (
            f"OS #{os.id} reprovada\n"
            f"{v}\n"
            f"Valor: {valor}\n\n"
            f"Detalhes: {link}"
        )

    if evento == "encerrada":
        return (
            f"OS #{os.id} encerrada\n"
            f"{v}\n"
            f"Custo final: {valor}\n\n"
            f"Detalhes: {link}"
        )

    # fallback genérico
    return (
        f"Atualização na OS #{os.id}\n"
        f"{v}\n"
        f"Status: {os.status}\n\n"
        f"Ver: {link}"
    )


# --- Dispatch ------------------------------------------------------------

def _enviar_via_notifier(telefone: str, mensagem: str, tag: str) -> dict:
    """POST pro notifier central. Ele cuida da janela + Evolution."""
    if not telefone:
        return {"sent": False, "error": "telefone vazio"}
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
        return {"sent": True, "via": "notifier"}
    except httpx.HTTPError as e:
        log.exception("Notifier falhou (tag=%s): %s", tag, e)
        return {"sent": False, "error": str(e)}


def _clean_phone(tel: Optional[str]) -> Optional[str]:
    if not tel:
        return None
    s = "".join(ch for ch in tel if ch.isdigit())
    return s or None


async def _destinatarios_por_papel(
    db: AsyncSession, filial_id: int, papeis: Iterable[str],
) -> list[User]:
    """Membros ativos com papel na filial (ou papel global, filial 0)."""
    stmt = (
        select(User)
        .join(MembroManutencao, MembroManutencao.user_id == User.id)
        .where(
            MembroManutencao.ativo.is_(True),
            MembroManutencao.papel.in_(list(papeis)),
            MembroManutencao.filial_id.in_([filial_id, 0]),
        )
    )
    return list((await db.execute(stmt)).scalars().all())


# Mapa evento -> papeis destinatários no fluxo real
DESTINOS = {
    "aberta":                ("filial_responsavel", "admin"),
    "aguardando_aprovacao":  ("admin",),
    "auto_aprovada":         ("filial_responsavel",),
    "aprovada":              ("filial_responsavel", "mecanico_interno"),
    "reprovada":             ("filial_responsavel",),
    "encerrada":             ("filial_responsavel",),
}


async def notify_os_transition(
    db: AsyncSession, os: OrdemServico, evento: str,
) -> dict:
    """Enfileira notificação WhatsApp pros papéis destinatários do evento.

    - Se EVOLUTION_ENABLED=false: só loga (não envia). Seguro pra dev.
    - Se true: dispatch pro notifier. Idempotência é responsabilidade do notifier.
    - Retorna resumo de quantos foram disparados.
    """
    papeis = DESTINOS.get(evento)
    if not papeis:
        return {"sent": 0, "skipped": "evento sem papeis mapeados"}

    dest = await _destinatarios_por_papel(db, os.filial_id, papeis)
    if not dest:
        log.warning("notify_os_transition · nenhum membro pros papeis %s na filial %s",
                    papeis, os.filial_id)
        return {"sent": 0, "skipped": "sem destinatarios"}

    enviados = 0
    for u in dest:
        tel = _clean_phone(u.telefone) or _clean_phone(settings.RENATO_WHATSAPP)
        msg = render(evento, os, destinatario=u)
        tag = f"manutencao:{evento}:{os.id}:{u.id}"

        if not settings.EVOLUTION_ENABLED:
            log.info("MOCK Zap · tag=%s · para=%s · %s", tag, u.email, msg.split(chr(10))[0])
            continue

        r = _enviar_via_notifier(tel, msg, tag)
        if r.get("sent"):
            enviados += 1
    return {"sent": enviados, "destinatarios": len(dest), "evento": evento}


# --- Retrocompat com o router de alertas manual ---------------------------

def render_template(
    tipo: str,
    template: Optional[str],
    os: Optional[OrdemServico] = None,
    veiculo: Optional[VeiculoSnapshot] = None,
) -> str:
    """Compat com router /alertas/preview (código antigo com emoji)."""
    if os and tipo in ("aberta","aguardando_aprovacao","aprovada","reprovada","encerrada"):
        return render(tipo, os)
    # Fallback minimalista sem emoji
    placa = veiculo.placa if veiculo else (os.veiculo.placa if os and os.veiculo else "?")
    modelo = veiculo.modelo if veiculo else (os.veiculo.modelo if os and os.veiculo else "?")
    return f"Atualização em {placa} ({modelo}) — {tipo}"


def dispatch_alerta(alerta: AlertaHistory) -> dict:
    """Envia o alerta. Mock se EVOLUTION_ENABLED=false; real via notifier se true."""
    if not settings.EVOLUTION_ENABLED:
        alerta.status = "sent"
        alerta.sent_at = datetime.utcnow()
        log.info("MOCK · tag=%s", alerta.tipo_alerta)
        return {"sent": False, "mock": True, "preview": alerta.mensagem}

    result = _enviar_via_notifier(
        telefone=_clean_phone(alerta.telefone) or _clean_phone(settings.RENATO_WHATSAPP) or "",
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
