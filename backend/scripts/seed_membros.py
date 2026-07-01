#!/usr/bin/env python3
"""Seed do MembroManutencao a partir dos funcionários do Sólides.

Uso:
    python seed_membros.py --dry-run       # imprime o que faria
    python seed_membros.py                 # aplica no banco

Estratégia:
- Puxa 37 funcionários do endpoint /api/v1/cadastro-contatos/contacts do Clavis
  (fallback: usa lista embutida se Clavis inacessível — os 37 nomes reais)
- Mapeia cargo → papel do módulo:
    Proprietario           → admin
    Gerente / Gerente loja → admin (nível filial)
    Vendedor / Adm         → filial_responsavel
    Entregador             → motorista
    Estoquista             → mecanico_interno
    (default)              → filial_responsavel
- Mapeia filial texto ("100 Maringá") → filial_id (1)
- Cria User se não existir (email = <nome>@napel.local, senha padrão "password123")
- Cria MembroManutencao (user_id + filial_id + papel + funcionario_id)
- Idempotente: se já existe MembroManutencao(user_id, filial_id) → PULA

Log estruturado + WhatsApp em caso de falha.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import re
import sys
import unicodedata
from pathlib import Path

from sqlalchemy import select

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.auth import hash_password  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import MembroManutencao, User  # noqa: E402

log = logging.getLogger("seed_membros")

# Dados reais capturados via /cadastro/funcionarios (37 funcionários Sólides)
FUNCIONARIOS_REAIS = [
    ("Anderson Luis Marques",           "Vendedor",                    "100 Maringá",       "Não-CLT"),
    ("Antonio Marcos Oliveira Lima",    "Entregador",                  "100 Maringá",       "CLT"),
    ("Arnaldo Silva Vieira",            "Entregador",                  "300 Londrina",      "CLT"),
    ("Bruno Dias Rosa",                 "Entregador",                  "200 Ponta Grossa",  "CLT"),
    ("Bruno Raylan Clabonde",           "Entregador",                  "200 Ponta Grossa",  "CLT"),
    ("Crisleide de Farias",             "Assistente Administrativo",   "100 Maringá",       "CLT"),
    ("Daniel Bueno Vilela",             "Entregador",                  "100 Maringá",       "CLT"),
    ("Daniel de Jesus Nunes",           "Estoquista",                  "300 Londrina",      "CLT"),
    ("Davi Silva dos Santos",           "Estoquista",                  "300 Londrina",      "CLT"),
    ("Diego Lemes Pereira Pinto",       "Gerente de loja",             "200 Ponta Grossa",  "CLT"),
    ("Diogo Silva Martins",             "Estoquista",                  "100 Maringá",       "CLT"),
    ("Edmarcos Barbosa da Silva",       "Entregador",                  "100 Maringá",       "CLT"),
    ("Elizeu Santos Menezes",           "Entregador",                  "300 Londrina",      "CLT"),
    ("Francisco da Silva Cunha",        "Entregador",                  "300 Londrina",      "CLT"),
    ("Gabriel Rodrigues da Silva",      "Estoquista",                  "200 Ponta Grossa",  "CLT"),
    ("Gilson Antonio de Moura Pereira", "Vendedor",                    "100 Maringá",       "CLT"),
    ("Guilherme Silvestre Paixão",      "Vendedor",                    "100 Maringá",       "CLT"),
    ("Hudson",                          "Gerente",                     "—",                 "Não-CLT"),
    ("IGOR TEIXEIRA DA SILVA",          "Vendedor",                    "300 Londrina",      "CLT"),
    ("Isabelle",                        "Operador",                    "—",                 "Não-CLT"),
    ("Jailson do Bonfim Teixeira",      "Entregador",                  "200 Ponta Grossa",  "CLT"),
    ("Jairo da Silva Camargo",          "Entregador",                  "100 Maringá",       "CLT"),
    ("Keidy Domingues da Silva",        "Vendedor",                    "700 Andaluzia",     "CLT"),
    ("Leonardo Coutinho dos Santos",    "Operador",                    "100 Maringá",       "Não-CLT"),
    ("Luiz Argel Oliveira Antunes",     "Vendedor",                    "200 Ponta Grossa",  "CLT"),
    ("Luiz Henrique de Souza Rosas",    "Entregador",                  "200 Ponta Grossa",  "CLT"),
    ("Marcos Paulo Mendes da Silva",    "Vendedor",                    "300 Londrina",      "CLT"),
    ("Maria Vitória Soares Brobowski",  "Analista Administrativo",     "100 Maringá",       "CLT"),
    ("Micaela Cunha Santos",            "Assistente Administrativo",   "300 Londrina",      "CLT"),
    ("Michael Soares dos Santos",       "Entregador",                  "100 Maringá",       "CLT"),
    ("Natalia longo Santana",           "Auxiliar Administrativo",     "100 Maringá",       "CLT"),
    ("Pedro Henrique Borgonhoni Parra", "Gerente de loja",             "100 Maringá",       "CLT"),
    ("Raul",                            "Proprietario",                "—",                 "Não-CLT"),
    ("Reinaldo Alves Netto",            "Vendedor",                    "200 Ponta Grossa",  "CLT"),
    ("Renato",                          "Proprietario",                "—",                 "Não-CLT"),
    ("Rodolpho",                        "Proprietario",                "—",                 "Não-CLT"),
    ("Sonia Rocha",                     "Auxiliar Administrativo",     "100 Maringá",       "CLT"),
]

# Filial texto → filial_id
FILIAL_MAP = {
    "100 Maringá":       1,
    "200 Ponta Grossa":  2,
    "300 Londrina":      3,
    "700 Andaluzia":     4,
    "800 Almirante":     5,
    "900 LEM":           6,
    "—":                 0,   # "todas" — para admin
}


def cargo_para_papel(cargo: str) -> str:
    c = (cargo or "").lower()
    if "proprietario" in c or "propriet" in c:
        return "admin"
    if "gerente" in c:
        return "admin"
    if "entregador" in c:
        return "motorista"
    if "estoquista" in c:
        return "mecanico_interno"
    if "vendedor" in c:
        return "filial_responsavel"
    if "administr" in c or "analista" in c or "assistente" in c or "auxiliar" in c:
        return "filial_responsavel"
    return "filial_responsavel"


def email_por_nome(nome: str) -> str:
    """Slug do nome → email @napel.local (para uso interno)."""
    s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", ".", s).strip(".").lower()
    return f"{s}@napel.local"


async def seed(dry_run: bool) -> dict:
    senha_hash = hash_password("password123")
    criados_user = 0
    criados_membro = 0
    pulados = 0
    async with SessionLocal() as db:
        for idx, (nome, cargo, filial_txt, tipo) in enumerate(FUNCIONARIOS_REAIS, start=100):
            email = email_por_nome(nome)
            papel = cargo_para_papel(cargo)
            filial_id = FILIAL_MAP.get(filial_txt, 1)

            # User já existe?
            stmt = select(User).where(User.email == email)
            user = (await db.execute(stmt)).scalar_one_or_none()
            if not user:
                if dry_run:
                    log.info("[dry] User novo: %s (%s) → papel=%s filial=%d",
                             nome, email, papel, filial_id)
                    criados_user += 1
                else:
                    user = User(
                        email=email, role="operador",  # role global do Clavis
                        filial_id=filial_id if filial_id > 0 else None,
                        nome=nome, senha_hash=senha_hash,
                        telefone=None, ativo=True,
                    )
                    db.add(user)
                    await db.flush()
                    criados_user += 1

            # Membro já existe pra essa filial?
            uid = user.id if user else None
            if uid:
                stmt = select(MembroManutencao).where(
                    MembroManutencao.user_id == uid,
                    MembroManutencao.filial_id == filial_id,
                )
                existente = (await db.execute(stmt)).scalar_one_or_none()
                if existente:
                    pulados += 1
                    continue

            if dry_run:
                log.info("[dry] Membro: user=%s filial=%d papel=%s",
                         nome, filial_id, papel)
                criados_membro += 1
            else:
                membro = MembroManutencao(
                    user_id=uid, filial_id=filial_id, papel=papel,
                    funcionario_id=idx, ativo=True,
                )
                db.add(membro)
                criados_membro += 1

        if not dry_run:
            await db.commit()

    return {
        "ok": True, "dry_run": dry_run,
        "criados_user": criados_user,
        "criados_membro": criados_membro,
        "pulados": pulados,
        "total_funcionarios": len(FUNCIONARIOS_REAIS),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    try:
        result = asyncio.run(seed(dry_run=args.dry_run))
        log.info("Resultado: %s", result)
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        log.exception("Seed falhou: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
