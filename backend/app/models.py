"""Schema completo do módulo Manutenção Veicular (13 tabelas).

Padrão Clavis: `String(N) + CheckConstraint` no lugar de `SQLEnum` (todos os
módulos do Clavis fazem assim — `SQLEnum` no Postgres tem migração frágil).

Match com docs/spec.md seção 3 e ADRs 02, 03, 04, 08, 09.
"""
from __future__ import annotations

import uuid

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Column, Date, DateTime,
    ForeignKey, Index, Integer, Numeric, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .database import Base


# ---------- Vocabulário de String-enums (validado por CheckConstraint) ----------

TIPO_OS_VALORES = (
    "corretiva_manual",
    "corretiva_checklist",
    "preventiva_automatica",
    "devolucao",
    "sinistro",   # v3: pipefy Custos - Sinistros
    "recall",     # v3: pipefy Custos - Recalls
)

STATUS_OS_VALORES = (
    "rascunho",
    "aberta",
    "em_triagem",              # NOVO (v3)
    "aguardando_orcamento",    # renomeia aguardando_anexos
    "aguardando_aprovacao",    # NOVO (v3)
    "em_execucao",             # aprovada + em execução
    "aguardando_peca",         # NOVO (v3)
    "encerrada",
    "cancelada",
)

TIPO_ANEXO_VALORES = (
    "foto_hodometro",
    "foto_problema",
    "foto_pneu",     # v3: TWI, com posicao_pneu
    "nf",
    "orcamento",
    "comprovante_pagamento",
)

TIPO_ITEM_VALORES = ("peca", "servico", "ajuste")

URGENCIA_VALORES = ("parado", "roda_com_reparo", "cosmetico")

TIPO_DESTINO_VALORES = ("oficina_terceirizada", "mecanico_interno", "concessionaria")

CATEGORIA_VALORES = (
    # 10 valores do campo "Tipo" do pipe Custos - Manutenção Veiculos (Pipefy)
    "Motor", "Pneu", "Pastilha / Lona", "Relação", "Lâmpadas",
    "Elétrica", "Bateria", "Empilhadeira", "Embreagem", "Outros",
)

MOTIVO_APROVACAO_VALORES = ("manual", "auto")

PAPEL_MEMBRO_VALORES = (
    "admin",
    "filial_responsavel",
    "motorista",
    "mecanico_interno",
    "admin_oficinas",
    "financeiro",
)

POSICAO_PNEU_VALORES = (
    "unico",                    # moto (sem lados)
    "dianteiro_motorista",
    "dianteiro_passageiro",
    "traseiro_motorista",
    "traseiro_passageiro",
    "dianteiro", "traseiro",    # moto simplificada
)


def _check_in(coluna: str, valores: tuple[str, ...], nome: str) -> CheckConstraint:
    """Helper para gerar CheckConstraint `coluna IN ('a','b',...)`."""
    lista = ",".join(f"'{v}'" for v in valores)
    return CheckConstraint(f"{coluna} IN ({lista})", name=nome)


# ---------- User (auth seed) ----------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(120), unique=True, nullable=False)
    role = Column(String(40), nullable=False)
    filial_id = Column(Integer, nullable=True)  # None = admin global
    nome = Column(String(120), nullable=False)
    senha_hash = Column(String(200), nullable=False)
    telefone = Column(String(20))
    ativo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login_at = Column(DateTime(timezone=True))


# ---------- Membro da Manutenção (mapeia user → papel do módulo) ----------
class MembroManutencao(Base):
    """Amarra User (Clavis) ↔ papel na manutenção ↔ filial ↔ funcionario (Sólides).

    Um user pode ter mais de uma linha se cobre várias filiais.
    """
    __tablename__ = "manutencao_membro"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    filial_id = Column(Integer, nullable=False, index=True)
    papel = Column(String(24), nullable=False)
    funcionario_id = Column(Integer, nullable=True)  # ID Sólides
    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "filial_id", name="uq_membro_user_filial"),
        _check_in("papel", PAPEL_MEMBRO_VALORES, "ck_membro_papel"),
    )


# ---------- Veículos (read-only cache do Controle Patrimonial) ----------
class VeiculoSnapshot(Base):
    __tablename__ = "veiculo_snapshot"

    id = Column(Integer, primary_key=True)
    veiculo_patrimonial_id = Column(Integer, unique=True, nullable=False)
    frota_external_id = Column(String(64), unique=True, index=True)
    placa = Column(String(10), unique=True, nullable=False)
    modelo = Column(String(100), nullable=False)
    marca = Column(String(80))
    tipo = Column(String(20))  # moto | carro | empilhadeira
    ano = Column(Integer)
    km_atual = Column(Integer, default=0, nullable=False)
    filial_id = Column(Integer, nullable=False)
    vencimento_crlv = Column(Date)
    responsavel_atual = Column(String(120))
    ativo = Column(Boolean, default=True, nullable=False)
    data_sincronismo = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_veiculo_filial", "filial_id", "modelo"),
        CheckConstraint("km_atual >= 0 AND km_atual <= 10000000", name="ck_km_range"),
        _check_in("tipo", ("moto", "carro", "empilhadeira"), "ck_veiculo_tipo"),
    )


# ---------- Oficinas (catálogo padronizado) ----------
class OficinaPadronizada(Base):
    __tablename__ = "oficina_padronizada"

    id = Column(Integer, primary_key=True)
    nome = Column(String(120), nullable=False)
    nome_normalizado = Column(String(120), index=True)  # v3: p/ dedup ("DIDA", "DIDA MOTOS" → "DIDA")
    cnpj = Column(String(20), unique=True)
    telefone = Column(String(30))
    cidade = Column(String(80))
    uf = Column(String(2))
    regiao_filial = Column(String(50))
    especialidade = Column(String(40))
    valor_servico_padrao = Column(Numeric(10, 2))
    avaliacao = Column(Numeric(3, 1))
    filial_id_preferencial = Column(Integer)
    ativa = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("nome", name="uk_oficina_nome"),
        Index("idx_oficina_ativa_uf", "ativa", "uf"),
    )


# ---------- OS-Manutenção (entidade central, v3) ----------
class OrdemServico(Base):
    __tablename__ = "os_manutencao"

    id = Column(Integer, primary_key=True)
    request_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)

    # Import dedupe (v3: Pipefy Custos - Manutenção Veiculos)
    pipefy_card_id = Column(String(20), unique=True, index=True, nullable=True)

    veiculo_id = Column(Integer, ForeignKey("veiculo_snapshot.id"), nullable=False)
    filial_id = Column(Integer, nullable=False)
    tipo_os = Column(String(24), nullable=False)
    status = Column(String(24), default="rascunho", nullable=False)
    categoria = Column(String(20), nullable=True)         # v3: campo Tipo do pipe
    urgencia = Column(String(20), nullable=True)          # v3
    tipo_destino = Column(String(24), default="oficina_terceirizada", nullable=False)  # v3

    data_abertura = Column(DateTime(timezone=True), server_default=func.now())
    data_encerramento = Column(DateTime(timezone=True))
    data_agendada = Column(Date)
    prazo_estimado_dias = Column(Integer)

    km_veiculo = Column(Integer, nullable=False)
    km_api_snapshot = Column(Integer)

    oficina_id = Column(Integer, ForeignKey("oficina_padronizada.id"), nullable=True)
    valor_total = Column(Numeric(12, 2), default=0, nullable=False)
    desconto_ajuste = Column(Numeric(10, 2), default=0)
    economia_napel_total = Column(Numeric(10, 2), default=0)

    garantia_peca_dias = Column(Integer)
    garantia_servico_dias = Column(Integer)
    garantia_observacoes = Column(Text)
    descricao_problema = Column(Text)
    observacoes_internas = Column(Text)

    # v3: Texto livre migrado do pipe ("Qtdes Peças/Serviços Trocadas")
    descricao_itens_original = Column(Text, nullable=True)

    # v3: Aprovação
    aprovado_por_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    aprovado_em = Column(DateTime(timezone=True))
    motivo_aprovacao = Column(String(16), nullable=True)   # None | 'manual' | 'auto'
    motivo_reprovacao = Column(Text)

    # v3: Reabertura em garantia (vínculo, não estado)
    reaberta_de_os_id = Column(Integer, ForeignKey("os_manutencao.id"), nullable=True)

    # v3: Identidades — quem operou vs quem é sujeito
    aberto_por_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    funcionario_relator_id = Column(Integer, nullable=True)  # ID Sólides

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), index=True)  # v3: index p/ helper _ativas

    veiculo = relationship("VeiculoSnapshot")
    oficina = relationship("OficinaPadronizada")
    itens = relationship("OsItemLinha", back_populates="os", cascade="all, delete-orphan")
    anexos = relationship("AnexosOs", back_populates="os", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_os_filial_status_data", "filial_id", "status", "data_abertura"),
        Index("idx_os_veiculo_data", "veiculo_id", "data_abertura"),
        CheckConstraint("km_veiculo >= 0 AND km_veiculo <= 10000000", name="ck_km_os_range"),
        _check_in("tipo_os", TIPO_OS_VALORES, "ck_os_tipo"),
        _check_in("status", STATUS_OS_VALORES, "ck_os_status"),
        _check_in("tipo_destino", TIPO_DESTINO_VALORES, "ck_os_tipo_destino"),
        CheckConstraint(
            f"urgencia IS NULL OR urgencia IN ({','.join(repr(v) for v in URGENCIA_VALORES)})",
            name="ck_os_urgencia",
        ),
        CheckConstraint(
            f"categoria IS NULL OR categoria IN ({','.join(repr(v) for v in CATEGORIA_VALORES)})",
            name="ck_os_categoria",
        ),
        CheckConstraint(
            f"motivo_aprovacao IS NULL OR motivo_aprovacao IN ({','.join(repr(v) for v in MOTIVO_APROVACAO_VALORES)})",
            name="ck_os_motivo_aprovacao",
        ),
    )


# ---------- Itens linha-a-linha ----------
class OsItemLinha(Base):
    __tablename__ = "os_item_linha"

    id = Column(Integer, primary_key=True)
    os_id = Column(Integer, ForeignKey("os_manutencao.id", ondelete="CASCADE"), nullable=False)
    tipo_item = Column(String(16), nullable=False)
    descricao = Column(String(200), nullable=False)
    sige_peca_id = Column(Integer)
    sige_sku = Column(String(40))
    quantidade = Column(Numeric(10, 3), default=1, nullable=False)
    valor_unitario = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)
    garantia_dias = Column(Integer, default=0)
    economia_napel = Column(Numeric(10, 2))

    os = relationship("OrdemServico", back_populates="itens")

    __table_args__ = (
        Index("idx_os_item_os", "os_id"),
        Index("idx_os_item_sige", "sige_sku"),
        Index("idx_item_garantia_ativa", "os_id", "garantia_dias"),  # v3: para expirar_garantias
        _check_in("tipo_item", TIPO_ITEM_VALORES, "ck_item_tipo"),
    )


# ---------- Anexos ----------
class AnexosOs(Base):
    __tablename__ = "anexos_os"

    id = Column(Integer, primary_key=True)
    os_id = Column(Integer, ForeignKey("os_manutencao.id", ondelete="CASCADE"), nullable=False)
    tipo = Column(String(24), nullable=False)
    posicao_pneu = Column(String(24), nullable=True)  # v3: usado quando tipo=foto_pneu
    arquivo_url = Column(Text, nullable=False)
    file_hash = Column(String(64))
    size_bytes = Column(BigInteger)
    mime_type = Column(String(80))
    filename_original = Column(String(200))
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    os = relationship("OrdemServico", back_populates="anexos")

    __table_args__ = (
        Index("idx_anexos_os", "os_id", "tipo"),
        _check_in("tipo", TIPO_ANEXO_VALORES, "ck_anexo_tipo"),
        CheckConstraint(
            f"posicao_pneu IS NULL OR posicao_pneu IN ({','.join(repr(v) for v in POSICAO_PNEU_VALORES)})",
            name="ck_anexo_posicao_pneu",
        ),
    )


# ---------- Planos preventivos ----------
class PlanoPreventiva(Base):
    __tablename__ = "plano_preventiva"

    id = Column(Integer, primary_key=True)
    modelo_veiculo = Column(String(100), nullable=False)
    item = Column(String(120), nullable=False)
    descricao = Column(Text)
    km_intervalo = Column(Integer)
    dias_intervalo = Column(Integer)
    antecedencia_dias = Column(Integer, default=7, nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ---------- Preventivas geradas ----------
class PreventivaGerada(Base):
    __tablename__ = "preventiva_gerada"

    id = Column(Integer, primary_key=True)
    veiculo_id = Column(Integer, ForeignKey("veiculo_snapshot.id"), nullable=False)
    plano_id = Column(Integer, ForeignKey("plano_preventiva.id"), nullable=False)
    os_id = Column(Integer, ForeignKey("os_manutencao.id"))
    ano_mes = Column(String(7), nullable=False)
    data_geracao = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("veiculo_id", "plano_id", "ano_mes", name="uk_preventiva_dedup"),
        Index("idx_preventiva_data", "data_geracao"),
    )


# ---------- Idempotency-Key cache ----------
class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    request_id = Column(UUID(as_uuid=True), primary_key=True)
    resource_type = Column(String(40), nullable=False)
    resource_id = Column(Integer, nullable=False)
    response_json = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ---------- Auditoria ----------
class AuditoriaOs(Base):
    __tablename__ = "auditoria_os"

    # Integer basta (max 2.1B ~ 5000 anos de OSs na escala Napel).
    # SQLite só auto-increment INTEGER PK; BigInteger não.
    id = Column(Integer, primary_key=True, autoincrement=True)
    os_id = Column(Integer)
    operacao = Column(String(80), nullable=False)  # "status:aguardando_orcamento->aguardando_aprovacao" = 45+ chars
    user_id = Column(Integer)
    filial_id = Column(Integer)
    before_data = Column(JSONB)
    after_data = Column(JSONB)
    motivo = Column(Text)
    ip_addr = Column(String(45))
    user_agent = Column(String(300))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_audit_os_date", "os_id", "timestamp"),
        Index("idx_audit_user_date", "user_id", "timestamp"),
    )


# ---------- Cache trocas de óleo ----------
class TrocaOleoCache(Base):
    __tablename__ = "troca_oleo_cache"

    id = Column(Integer, primary_key=True)
    veiculo_id = Column(Integer, nullable=False)
    placa = Column(String(10))
    data_troca = Column(DateTime(timezone=True), nullable=False)
    km = Column(Integer)
    oficina_nome = Column(String(120))
    produto = Column(String(120))
    litros = Column(Numeric(5, 2))
    valor = Column(Numeric(10, 2))
    dedup_hash = Column(String(64), unique=True, nullable=False)
    data_sincronismo = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("idx_troca_oleo_veiculo", "veiculo_id", "data_troca"),)


# ---------- SIGE staging ----------
class SigePecaStaging(Base):
    __tablename__ = "sige_peca_staging"

    id = Column(Integer, primary_key=True)
    codigo_sige = Column(String(50), unique=True, nullable=False)
    descricao = Column(String(200), nullable=False)
    preco_custo = Column(Numeric(10, 2))
    preco_mercado_ml = Column(Numeric(10, 2))
    estoque_atual = Column(Integer)
    eh_napel = Column(Boolean, default=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


# ---------- Alertas WhatsApp ----------
class AlertaHistory(Base):
    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True)
    os_id = Column(Integer, ForeignKey("os_manutencao.id"))
    veiculo_id = Column(Integer, ForeignKey("veiculo_snapshot.id"))
    filial_id = Column(Integer)
    tipo_alerta = Column(String(40), nullable=False)  # preventiva_km | preventiva_data | documento | recall | checklist_atrasado | garantia | manual
    telefone = Column(String(30), nullable=False)
    template_name = Column(String(80), nullable=False)
    mensagem = Column(Text)
    status = Column(String(20), nullable=False)  # pending | sent | failed | retry | dlq
    retry_count = Column(Integer, default=0)
    error_msg = Column(Text)
    enviado_por = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sent_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_alert_phone_date", "telefone", "created_at"),
        Index("idx_alert_status", "status", "created_at"),
    )
