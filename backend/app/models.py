"""Schema completo do módulo Manutenção Veicular (12 tabelas + enums).

Match com docs/spec.md seção 3 (Schema do banco) e arquitetura.md ADRs 02, 03, 04, 08, 09.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Column, Date, DateTime,
    Enum as SQLEnum, ForeignKey, Index, Integer, Numeric, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .database import Base


# ---------- Enums ----------
class TipoOsEnum(str, enum.Enum):
    corretiva_manual = "corretiva_manual"
    corretiva_checklist = "corretiva_checklist"
    preventiva_automatica = "preventiva_automatica"
    devolucao = "devolucao"


class StatusOsEnum(str, enum.Enum):
    rascunho = "rascunho"
    aberta = "aberta"
    aguardando_anexos = "aguardando_anexos"
    pronta_execucao = "pronta_execucao"
    em_execucao = "em_execucao"
    encerrada = "encerrada"
    cancelada = "cancelada"


class TipoAnexoEnum(str, enum.Enum):
    foto_hodometro = "foto_hodometro"
    foto_problema = "foto_problema"
    nf = "nf"
    orcamento = "orcamento"


class TipoItemEnum(str, enum.Enum):
    peca = "peca"
    servico = "servico"
    ajuste = "ajuste"


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


# ---------- Veículos (read-only cache do Controle Patrimonial) ----------
class VeiculoSnapshot(Base):
    __tablename__ = "veiculo_snapshot"

    id = Column(Integer, primary_key=True)
    veiculo_patrimonial_id = Column(Integer, unique=True, nullable=False)
    # UUID hex usado pela Frota (frota.demos.napel.com.br) e app Troca de Óleo
    # como chave global do veículo cross-módulo
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
    )


# ---------- Oficinas (catálogo padronizado — texto livre bloqueado) ----------
class OficinaPadronizada(Base):
    __tablename__ = "oficina_padronizada"

    id = Column(Integer, primary_key=True)
    nome = Column(String(120), nullable=False)
    cnpj = Column(String(20), unique=True)
    telefone = Column(String(30))
    cidade = Column(String(80))
    uf = Column(String(2))
    regiao_filial = Column(String(50))
    especialidade = Column(String(40))  # moto | carro | pneu | empilhadeira
    valor_servico_padrao = Column(Numeric(10, 2))
    avaliacao = Column(Numeric(3, 1))  # 0.0 a 5.0
    filial_id_preferencial = Column(Integer)
    ativa = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("nome", name="uk_oficina_nome"),
        Index("idx_oficina_ativa_uf", "ativa", "uf"),
    )


# ---------- OS-Manutenção (entidade central) ----------
class OrdemServico(Base):
    __tablename__ = "os_manutencao"

    id = Column(Integer, primary_key=True)
    request_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    veiculo_id = Column(Integer, ForeignKey("veiculo_snapshot.id"), nullable=False)
    filial_id = Column(Integer, nullable=False)
    tipo_os = Column(SQLEnum(TipoOsEnum, name="tipo_os_enum"), nullable=False)
    status = Column(SQLEnum(StatusOsEnum, name="status_os_enum"),
                    default=StatusOsEnum.rascunho, nullable=False)

    data_abertura = Column(DateTime(timezone=True), server_default=func.now())
    data_encerramento = Column(DateTime(timezone=True))
    data_agendada = Column(Date)
    prazo_estimado_dias = Column(Integer)

    km_veiculo = Column(Integer, nullable=False)
    km_api_snapshot = Column(Integer)  # snapshot do Patrimonial no momento

    oficina_id = Column(Integer, ForeignKey("oficina_padronizada.id"))
    valor_total = Column(Numeric(12, 2), default=0, nullable=False)
    desconto_ajuste = Column(Numeric(10, 2), default=0)
    economia_napel_total = Column(Numeric(10, 2), default=0)  # V2

    garantia_peca_dias = Column(Integer)
    garantia_servico_dias = Column(Integer)
    garantia_observacoes = Column(Text)
    descricao_problema = Column(Text)
    observacoes_internas = Column(Text)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))

    veiculo = relationship("VeiculoSnapshot")
    oficina = relationship("OficinaPadronizada")
    itens = relationship("OsItemLinha", back_populates="os", cascade="all, delete-orphan")
    anexos = relationship("AnexosOs", back_populates="os", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_os_filial_status_data", "filial_id", "status", "data_abertura"),
        Index("idx_os_veiculo_data", "veiculo_id", "data_abertura"),
        CheckConstraint("km_veiculo >= 0 AND km_veiculo <= 10000000", name="ck_km_os_range"),
    )


# ---------- Itens linha-a-linha ----------
class OsItemLinha(Base):
    __tablename__ = "os_item_linha"

    id = Column(Integer, primary_key=True)
    os_id = Column(Integer, ForeignKey("os_manutencao.id", ondelete="CASCADE"), nullable=False)
    tipo_item = Column(SQLEnum(TipoItemEnum, name="tipo_item_enum"), nullable=False)
    descricao = Column(String(200), nullable=False)
    sige_peca_id = Column(Integer)  # V2: FK pra sige_peca_staging quando ativado
    sige_sku = Column(String(40))
    quantidade = Column(Numeric(10, 3), default=1, nullable=False)
    valor_unitario = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)
    garantia_dias = Column(Integer, default=0)
    economia_napel = Column(Numeric(10, 2))  # V2: lookup ML vs preço Napel

    os = relationship("OrdemServico", back_populates="itens")

    __table_args__ = (
        Index("idx_os_item_os", "os_id"),
        Index("idx_os_item_sige", "sige_sku"),
    )


# ---------- Anexos (foto + NF obrigatórias) ----------
class AnexosOs(Base):
    __tablename__ = "anexos_os"

    id = Column(Integer, primary_key=True)
    os_id = Column(Integer, ForeignKey("os_manutencao.id", ondelete="CASCADE"), nullable=False)
    tipo = Column(SQLEnum(TipoAnexoEnum, name="tipo_anexo_enum"), nullable=False)
    arquivo_url = Column(Text, nullable=False)
    file_hash = Column(String(64))
    size_bytes = Column(BigInteger)
    mime_type = Column(String(80))
    filename_original = Column(String(200))
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    os = relationship("OrdemServico", back_populates="anexos")

    __table_args__ = (Index("idx_anexos_os", "os_id", "tipo"),)


# ---------- Planos preventivos ----------
class PlanoPreventiva(Base):
    __tablename__ = "plano_preventiva"

    id = Column(Integer, primary_key=True)
    modelo_veiculo = Column(String(100), nullable=False)
    item = Column(String(120), nullable=False)  # "Filtro de ar", "Pastilha freio"
    descricao = Column(Text)
    km_intervalo = Column(Integer)
    dias_intervalo = Column(Integer)
    antecedencia_dias = Column(Integer, default=7, nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ---------- Preventivas geradas (dedup por modelo+plano+ano+mes) ----------
class PreventivaGerada(Base):
    __tablename__ = "preventiva_gerada"

    id = Column(Integer, primary_key=True)
    veiculo_id = Column(Integer, ForeignKey("veiculo_snapshot.id"), nullable=False)
    plano_id = Column(Integer, ForeignKey("plano_preventiva.id"), nullable=False)
    os_id = Column(Integer, ForeignKey("os_manutencao.id"))
    ano_mes = Column(String(7), nullable=False)  # 'YYYY-MM'
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


# ---------- Auditoria (LGPD + rastreabilidade) ----------
class AuditoriaOs(Base):
    __tablename__ = "auditoria_os"

    id = Column(BigInteger, primary_key=True)
    os_id = Column(Integer)
    operacao = Column(String(20), nullable=False)  # INSERT | UPDATE | DELETE | STATUS
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


# ---------- Cache trocas de óleo (read-only do app dedicado) ----------
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


# ---------- SIGE staging (vazio no MVP, ativado V2) ----------
class SigePecaStaging(Base):
    __tablename__ = "sige_peca_staging"

    id = Column(Integer, primary_key=True)
    codigo_sige = Column(String(50), unique=True, nullable=False)
    descricao = Column(String(200), nullable=False)
    preco_custo = Column(Numeric(10, 2))
    preco_mercado_ml = Column(Numeric(10, 2))  # cache ML
    estoque_atual = Column(Integer)
    eh_napel = Column(Boolean, default=False)  # peça Napel (suspensão/freio)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


# ---------- Alertas WhatsApp (Evolution) ----------
class AlertaHistory(Base):
    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True)
    os_id = Column(Integer, ForeignKey("os_manutencao.id"))
    veiculo_id = Column(Integer, ForeignKey("veiculo_snapshot.id"))
    filial_id = Column(Integer)
    tipo_alerta = Column(String(40), nullable=False)  # preventiva_proxima | os_aberta_dias | custo_fora_padrao | manual
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
