"""Criação de tabelas + seed completo da demo com dados reais do Pipefy."""
from __future__ import annotations

import logging
import random
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from .auth import hash_password
from .database import Base, SessionLocal, engine
from .models import (AnexosOs, OficinaPadronizada, OrdemServico, OsItemLinha,
                     PlanoPreventiva, StatusOsEnum, TipoAnexoEnum, TipoItemEnum,
                     TipoOsEnum, TrocaOleoCache, User, VeiculoSnapshot)

log = logging.getLogger("manutencao.bootstrap")


def init_database():
    Base.metadata.create_all(bind=engine)
    log.info("Tabelas criadas/verificadas.")
    _migrate_schema()


def _migrate_schema():
    """Adiciona colunas novas em tabelas existentes (Alembic ad-hoc pra demo).

    Tolerância: se a coluna já existe, ignora.
    """
    from sqlalchemy import text as sql_text
    migrations = [
        "ALTER TABLE veiculo_snapshot ADD COLUMN IF NOT EXISTS frota_external_id VARCHAR(64)",
        "ALTER TABLE veiculo_snapshot ADD COLUMN IF NOT EXISTS marca VARCHAR(80)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_veiculo_frota_external ON veiculo_snapshot(frota_external_id)",
    ]
    with engine.begin() as conn:
        for m in migrations:
            try:
                conn.execute(sql_text(m))
                log.info("migrate: %s", m[:80])
            except Exception as e:
                log.warning("migrate skip (%s): %s", m[:50], e)


def seed_all():
    db: Session = SessionLocal()
    try:
        if db.query(User).count() > 0:
            log.info("Seed já aplicado, pulando.")
            return
        log.info("Aplicando seed completo...")
        _seed_users(db)
        _seed_oficinas(db)
        _seed_veiculos(db)
        _seed_planos(db)
        _seed_trocas_oleo(db)
        _seed_os_historico(db)
        db.commit()
        log.info("Seed concluído: %d users, %d oficinas, %d veículos, %d OS",
                 db.query(User).count(), db.query(OficinaPadronizada).count(),
                 db.query(VeiculoSnapshot).count(), db.query(OrdemServico).count())
    except Exception:
        db.rollback()
        log.exception("Seed falhou")
        raise
    finally:
        db.close()


def _seed_users(db: Session):
    senha = hash_password("password123")
    users = [
        User(id=1, email="hudson@napel.local",            role="admin",               filial_id=None, nome="Hudson · Diretor",         senha_hash=senha, telefone="+5544999990000"),
        User(id=2, email="responsavel@maringa.local",     role="filial_responsavel",  filial_id=1,    nome="Responsável Maringá",       senha_hash=senha, telefone="+5544999995678"),
        User(id=3, email="responsavel@pg.local",          role="filial_responsavel",  filial_id=2,    nome="Responsável P. Grossa",     senha_hash=senha, telefone="+5542999991234"),
        User(id=4, email="responsavel@leme.local",        role="filial_responsavel",  filial_id=3,    nome="Responsável LEM",           senha_hash=senha, telefone="+5577999994321"),
        User(id=5, email="motorista@mobile.local",        role="motorista",           filial_id=1,    nome="Luiz Gustavo · Motorista",  senha_hash=senha, telefone="+5544999999999"),
        User(id=6, email="admin@oficinas.local",          role="admin_oficinas",      filial_id=None, nome="Admin Oficinas",            senha_hash=senha),
    ]
    db.add_all(users)
    db.flush()


def _seed_oficinas(db: Session):
    """Top 7 oficinas reais do Pipefy — texto livre bloqueado por UNIQUE."""
    rows = [
        ("DIDA MOTOS",        "12.345.678/0001-90", "Maringá",                "PR", 1, "moto", Decimal("216.00"),  4.5),
        ("LARANJA MECANICA",  "23.456.789/0001-01", "Maringá",                "PR", 1, "carro", Decimal("1953.00"), 3.5),
        ("Boldor Motos",      "34.567.890/0001-12", "Maringá",                "PR", 1, "moto", Decimal("215.00"),  4.7),
        ("AGUIA MOTOS",       "45.678.901/0001-23", "Ponta Grossa",           "PR", 2, "moto", Decimal("204.00"),  4.3),
        ("AK BORRACHARIA",    "56.789.012/0001-34", "Ponta Grossa",           "PR", 2, "pneu", Decimal("143.00"),  4.0),
        ("PK Motos",          "67.890.123/0001-45", "Luís Eduardo Magalhães", "BA", 3, "moto", Decimal("196.00"),  4.0),
        ("G & C MOTOS",       "78.901.234/0001-56", "Luís Eduardo Magalhães", "BA", 3, "moto", Decimal("85.00"),   4.0),
    ]
    for i, (n, c, cid, uf, fil, esp, vsp, av) in enumerate(rows, 1):
        db.add(OficinaPadronizada(
            id=i, nome=n, cnpj=c, cidade=cid, uf=uf,
            filial_id_preferencial=fil, especialidade=esp,
            valor_servico_padrao=vsp, avaliacao=Decimal(str(av)),
            telefone=f"+55 {44 + i} 99999-{1000 + i:04d}",
        ))
    db.flush()


def _seed_veiculos(db: Session):
    """14 veículos reais — placas extraídas do Pipefy."""
    veiculos = [
        # placa, modelo, tipo, ano, km, filial, crlv, responsavel
        ("BEO7H12", "STRADA ENDURANCE CS",  "carro",        2018,  99483, 1, "2026-08-31", "Luiz Gustavo"),
        ("BEE7G35", "CG 160 FAN",           "moto",         2022,  40000, 1, "2026-07-15", "Vinicius"),
        ("SDU2A60", "CG 160 FAN",           "moto",         2022,  78095, 2, "2026-09-10", "Erick"),
        ("EEE1111", "EMPILHADEIRA HYSTER",  "empilhadeira", 2020,      0, 1, None,         "Operador interno"),
        ("BEE2A87", "CG 160 FAN",           "moto",         2022, 166979, 3, "2026-06-20", "Allan Matheus"),
        ("RHX7J25", "CG 160 FAN",           "moto",         2022,  50000, 3, "2026-07-05", "Jailson"),
        ("PKL9438", "CG 125I FAN",          "moto",         2021,  60000, 1, "2026-05-30", "Francisco da Silva"),
        ("BAI7758", "CG 125 FAN KS",        "moto",         2020, 204688, 1, "2026-04-15", "Weslei"),
        ("RPL1B57", "CG 160 FAN",           "moto",         2022,  35000, 2, "2026-09-22", "Elizeu"),
        ("AZM1295", "MONTANA",              "carro",        2015, 198865, 1, "2026-12-31", "Arnaldo"),
        ("TAW7I30", "SAVEIRO CS RB MF",     "carro",        2024,   5000, 1, "2027-03-15", "Edmarcos"),
        ("AWA2816", "SAVEIRO 1.6 CS",       "carro",        2014, 320184, 1, "2026-10-05", "Hudson"),
        ("TAQ3J07", "SAVEIRO CS RB MF",     "carro",        2024,   1500, 3, "2027-04-20", "Daniel Bueno"),
        ("TAW7I29", "SAVEIRO CS RB MF",     "carro",        2024,   2000, 1, "2027-03-15", "Paulo Sergio"),
    ]
    for i, (placa, mod, tp, ano, km, fil, crlv, resp) in enumerate(veiculos, 1):
        db.add(VeiculoSnapshot(
            id=i, veiculo_patrimonial_id=1000 + i, placa=placa, modelo=mod,
            tipo=tp, ano=ano, km_atual=km, filial_id=fil,
            vencimento_crlv=date.fromisoformat(crlv) if crlv else None,
            responsavel_atual=resp,
        ))
    db.flush()


def _seed_planos(db: Session):
    planos = [
        ("CG 160 FAN",           "Filtro de ar",                10000, 365, 7),
        ("CG 160 FAN",           "Kit relação (corrente)",      20000, None, 14),
        ("CG 160 FAN",           "Lona freio traseiro",         15000, None, 14),
        ("CG 125 FAN KS",        "Filtro de ar",                10000, 365, 7),
        ("CG 125I FAN",          "Filtro de ar",                10000, 365, 7),
        ("STRADA ENDURANCE CS",  "Pastilha freio dianteira",    30000, None, 14),
        ("STRADA ENDURANCE CS",  "Filtro combustível",          20000, 365, 7),
        ("SAVEIRO CS RB MF",     "Suspensão dianteira",         60000, None, 30),
        ("SAVEIRO CS RB MF",     "Correia dentada",             60000, None, 30),
        ("MONTANA",              "Pastilha freio dianteira",    30000, None, 14),
        ("EMPILHADEIRA HYSTER",  "Revisão geral preventiva",    None,  180, 14),
        ("SAVEIRO 1.6 CS",       "Suspensão dianteira",         60000, None, 30),
    ]
    for i, (mod, item, km, dias, ant) in enumerate(planos, 1):
        db.add(PlanoPreventiva(
            id=i, modelo_veiculo=mod, item=item,
            descricao=f"{item} ({mod}) — intervalo: {km or '—'} km / {dias or '—'} dias",
            km_intervalo=km, dias_intervalo=dias, antecedencia_dias=ant, ativo=True,
        ))
    db.flush()


def _seed_trocas_oleo(db: Session):
    base = datetime(2024, 11, 1, 10, 0)
    oficinas_oleo = ["EMERSON PNEUS", "AK BORRACHARIA", "DIDA MOTOS"]
    for i in range(150):
        veiculo_id = (i % 14) + 1
        data = base + timedelta(days=i * 4)
        km = 1000 + i * 500
        valor = Decimal("280.00") if veiculo_id <= 4 else Decimal("180.00")
        db.add(TrocaOleoCache(
            veiculo_id=veiculo_id, data_troca=data, km=km,
            oficina_nome=oficinas_oleo[i % 3],
            produto="Lubrax 15W-40 sintético", litros=Decimal("4.00"),
            valor=valor, dedup_hash=f"oleo-{veiculo_id}-{data.date().isoformat()}-{i}",
        ))
    db.flush()


def _seed_os_historico(db: Session):
    """200 OS distribuídas em 19 meses — replica distribuição real do Pipefy."""
    random.seed(42)
    tipos_manutencao = [
        ("Motor",            "junta cabeçote",                 [400, 580, 850, 1200, 5683]),
        ("Pneu",             "remendo / troca pneu",           [50, 80, 100, 145, 250]),
        ("Pastilha / Lona",  "pastilha freio dianteira",       [90, 150, 200, 245, 320]),
        ("Relação",          "kit relação completo",           [180, 250, 290, 350]),
        ("Lâmpadas",         "lâmpada queimada",               [3, 5, 15, 25, 45]),
        ("Elétrica",         "diagnóstico elétrico",           [60, 120, 250, 500]),
        ("Embreagem",        "kit embreagem",                  [300, 450, 580]),
        ("Bateria",          "troca bateria",                  [180, 280, 450]),
        ("Outros",           "ajustes diversos",               [20, 50, 75, 150, 200]),
    ]
    base = datetime(2024, 10, 19, 10, 0)
    veiculos = db.query(VeiculoSnapshot).all()
    oficinas = db.query(OficinaPadronizada).all()
    admin_id = 1

    for i in range(200):
        veic = random.choice(veiculos)
        of = random.choice(oficinas)
        data = base + timedelta(days=i * 3 + random.randint(0, 2), hours=random.randint(0, 8))
        tipo_label, descr, faixa_valor = random.choice(tipos_manutencao)
        tipo_os = random.choices(
            [TipoOsEnum.corretiva_manual, TipoOsEnum.preventiva_automatica],
            weights=[7, 3], k=1,
        )[0]
        valor_item = Decimal(str(random.choice(faixa_valor)))

        # Distribuição de status: 70% encerrada, 8% em_execucao, 8% aguardando, 5% aberta, 5% pronta, 4% cancelada
        rnd = random.random()
        if   rnd < 0.70: status = StatusOsEnum.encerrada
        elif rnd < 0.78: status = StatusOsEnum.em_execucao
        elif rnd < 0.86: status = StatusOsEnum.aguardando_anexos
        elif rnd < 0.91: status = StatusOsEnum.aberta
        elif rnd < 0.96: status = StatusOsEnum.pronta_execucao
        else:            status = StatusOsEnum.cancelada

        data_enc = (data + timedelta(days=random.randint(1, 5))) if status == StatusOsEnum.encerrada else None

        os = OrdemServico(
            request_id=uuid.uuid4(),
            veiculo_id=veic.id, filial_id=veic.filial_id,
            tipo_os=tipo_os, status=status,
            data_abertura=data, data_encerramento=data_enc,
            km_veiculo=max(0, veic.km_atual - random.randint(0, 30000)),
            km_api_snapshot=max(0, veic.km_atual - random.randint(0, 30000)),
            oficina_id=of.id,
            valor_total=valor_item,
            descricao_problema=f"{tipo_label} — {descr}",
            created_by=admin_id,
            garantia_peca_dias=30, garantia_servico_dias=30,
        )
        db.add(os)
        db.flush()

        # Item linha-a-linha
        item_tipo = TipoItemEnum.servico if "freio" in descr or "diagnóstico" in descr else TipoItemEnum.peca
        db.add(OsItemLinha(
            os_id=os.id, tipo_item=item_tipo,
            descricao=descr, quantidade=Decimal("1"),
            valor_unitario=valor_item, subtotal=valor_item,
            garantia_dias=30,
        ))

        # Anexos seed (varia por status)
        if status == StatusOsEnum.encerrada and random.random() < 0.70:
            db.add(AnexosOs(
                os_id=os.id, tipo=TipoAnexoEnum.nf,
                arquivo_url=f"/uploads/seed/nf-{os.id:04d}.pdf",
                file_hash=f"seed{os.id:08x}",
                size_bytes=125_000, mime_type="application/pdf",
                filename_original=f"NF-{os.id:04d}.pdf",
                uploaded_by=admin_id,
            ))
        if random.random() < 0.55:
            db.add(AnexosOs(
                os_id=os.id, tipo=TipoAnexoEnum.foto_hodometro,
                arquivo_url=f"/uploads/seed/hodometro-{os.id:04d}.jpg",
                file_hash=f"seed{os.id + 100000:08x}",
                size_bytes=85_000, mime_type="image/jpeg",
                filename_original=f"hodometro-{os.id:04d}.jpg",
                uploaded_by=admin_id,
            ))
    db.flush()
