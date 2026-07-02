"""Normalização de nomes de oficina — copiado 1:1 do troca-oleo (offices.py).

Mantém os DOIS lados usando a MESMA regra de dedup ("DIDA MOTOS" -> "DIDA").
"""
from __future__ import annotations

import re
import unicodedata

_SUFIXOS = [
    "MOTOS", "MOTO", "MOTOR", "MOTORS", "AUTOPECAS", "AUTO PECAS",
    "AUTO", "OFICINA", "CENTER", "CENTRO AUTOMOTIVO", "AUTOMOTIVA",
    "AUTOMOTIVO", "LTDA", "ME", "EIRELI", "PECAS",
]

_ALIASES = {
    # Boldor e variações fonéticas comuns em digitação
    "BOOLDOOR": "BOLDOR",
    "BOOLDOR": "BOLDOR",
    "BOLDOOR": "BOLDOR",
    "BOUDOR": "BOLDOR",
    "BUDOR": "BOLDOR",
    "BOLDOOR": "BOLDOR",
    "BOULDOR": "BOLDOR",
    # Águia e variações
    "AGUI": "AGUIA",
    "AQUI": "AGUIA",
    "AQUIA": "AGUIA",
    # G E C
    "GEC": "G E C",
    "GC": "G E C",
    "GUAREZI": "GUAREZI",
    # Dida e variações
    "DIDDA": "DIDA",
}


def normalize_office(nome: str | None) -> str | None:
    if not nome:
        return None
    s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    s = s.upper().strip()
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    for suf in _SUFIXOS:
        s = re.sub(rf"\b{suf}\b", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        return None
    sem_espaco = s.replace(" ", "")
    if sem_espaco in _ALIASES:
        return _ALIASES[sem_espaco]
    if s in _ALIASES:
        return _ALIASES[s]
    return s


def display_office(canonico: str | None) -> str:
    if not canonico:
        return "—"
    return canonico.title()
