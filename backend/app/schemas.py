"""Schemas Pydantic v2 — espelha spec.md §5."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------- Auth ----------
class LoginRequest(BaseModel):
    email: str
    senha: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: int
    email: str
    nome: str
    role: str
    filial_id: Optional[int] = None
    telefone: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# ---------- Veículo ----------
class VeiculoOut(BaseModel):
    id: int
    placa: str
    modelo: str
    tipo: Optional[str] = None
    ano: Optional[int] = None
    km_atual: int
    filial_id: int
    vencimento_crlv: Optional[date] = None
    responsavel_atual: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# ---------- Oficina ----------
class OficinaBase(BaseModel):
    nome: str
    cnpj: Optional[str] = None
    telefone: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    especialidade: Optional[str] = None
    filial_id_preferencial: Optional[int] = None


class OficinaCreate(OficinaBase):
    pass


class OficinaOut(OficinaBase):
    id: int
    avaliacao: Optional[Decimal] = None
    valor_servico_padrao: Optional[Decimal] = None
    ativa: bool
    model_config = ConfigDict(from_attributes=True)


# ---------- Itens da OS ----------
class ItemLinhaIn(BaseModel):
    tipo_item: Literal["peca", "servico", "ajuste"]
    descricao: str
    sige_sku: Optional[str] = None
    sige_peca_id: Optional[int] = None
    quantidade: Decimal = Field(default=Decimal("1"), gt=0)
    valor_unitario: Decimal = Field(gt=0)
    garantia_dias: int = 0


class ItemLinhaOut(BaseModel):
    id: int
    tipo_item: str
    descricao: str
    sige_sku: Optional[str] = None
    quantidade: Decimal
    valor_unitario: Decimal
    subtotal: Decimal
    garantia_dias: int
    economia_napel: Optional[Decimal] = None
    model_config = ConfigDict(from_attributes=True)


# ---------- Anexos ----------
class AnexoOut(BaseModel):
    id: int
    tipo: str
    arquivo_url: str
    file_hash: Optional[str] = None
    size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    filename_original: Optional[str] = None
    uploaded_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ---------- Ordem de Serviço ----------
class OrdemServicoCreate(BaseModel):
    request_id: UUID
    veiculo_id: int
    tipo_os: Literal["corretiva_manual", "corretiva_checklist", "preventiva_automatica", "devolucao"]
    oficina_id: Optional[int] = None
    km_veiculo: int = Field(ge=0, le=10_000_000)
    descricao_problema: Optional[str] = None
    data_agendada: Optional[date] = None
    prazo_estimado_dias: Optional[int] = None
    itens: List[ItemLinhaIn] = []


class OrdemServicoUpdate(BaseModel):
    status: Optional[Literal[
        "rascunho", "aberta", "aguardando_anexos", "pronta_execucao",
        "em_execucao", "encerrada", "cancelada",
    ]] = None
    oficina_id: Optional[int] = None
    descricao_problema: Optional[str] = None
    garantia_peca_dias: Optional[int] = None
    garantia_servico_dias: Optional[int] = None
    garantia_observacoes: Optional[str] = None
    desconto_ajuste: Optional[Decimal] = None
    motivo_cancelamento: Optional[str] = None


class OrdemServicoOut(BaseModel):
    id: int
    request_id: UUID
    veiculo_id: int
    filial_id: int
    tipo_os: str
    status: str
    data_abertura: datetime
    data_encerramento: Optional[datetime] = None
    data_agendada: Optional[date] = None
    km_veiculo: int
    km_api_snapshot: Optional[int] = None
    oficina_id: Optional[int] = None
    valor_total: Decimal
    desconto_ajuste: Decimal
    economia_napel_total: Decimal
    garantia_peca_dias: Optional[int] = None
    garantia_servico_dias: Optional[int] = None
    descricao_problema: Optional[str] = None
    created_by: int
    updated_at: datetime
    # Campos derivados (preenchidos no router pra evitar lookups extras no front)
    veiculo_placa: Optional[str] = None
    veiculo_modelo: Optional[str] = None
    oficina_nome: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class OrdemServicoDetalhe(OrdemServicoOut):
    veiculo: VeiculoOut
    oficina: Optional[OficinaOut] = None
    itens: List[ItemLinhaOut] = []
    anexos: List[AnexoOut] = []


class ListaOSResponse(BaseModel):
    data: List[OrdemServicoOut]
    total: int
    limit: int
    offset: int


# ---------- Timeline ----------
class TimelineItem(BaseModel):
    tipo: Literal["os_manutencao", "troca_oleo", "checklist_v2", "patrimonial"]
    data: datetime
    titulo: str
    descricao: Optional[str] = None
    valor: Optional[Decimal] = None
    subtipo: Optional[str] = None
    status: Optional[str] = None
    economia: Optional[Decimal] = None
    oficina: Optional[str] = None
    ref_id: int


class VeiculoTimeline(BaseModel):
    veiculo: VeiculoOut
    items: List[TimelineItem]
    warnings: List[str] = []
    total_os: int
    custo_12m: Decimal
    cpk: Decimal


# ---------- Dashboard ----------
class DashboardFilial(BaseModel):
    cpk_acumulado_ytd: Decimal
    cpk_variacao_pct: Decimal
    custo_total_mes: Decimal
    os_no_mes: int
    ticket_medio: Decimal
    maior_os_mes: Decimal
    os_abertas: int
    os_atrasadas: int
    pct_preventiva_no_prazo: Decimal
    pct_com_nf: Decimal
    serie_temporal_12m: List[dict]
    distribuicao_tipo: List[dict]
    top_veiculos: List[dict]
    top_oficinas: List[dict]


# ---------- Planos preventivos ----------
class PlanoOut(BaseModel):
    id: int
    modelo_veiculo: str
    item: str
    descricao: Optional[str] = None
    km_intervalo: Optional[int] = None
    dias_intervalo: Optional[int] = None
    antecedencia_dias: int
    ativo: bool
    model_config = ConfigDict(from_attributes=True)


# ---------- Alertas WhatsApp ----------
class AlertaDispatch(BaseModel):
    os_id: Optional[int] = None
    veiculo_id: Optional[int] = None
    tipo_alerta: Literal["preventiva_proxima", "os_aberta_dias", "custo_fora_padrao", "solicitar_nf", "manual"]
    template: Optional[str] = None
    destinatario_user_id: Optional[int] = None
    telefone: Optional[str] = None


class AlertaPreview(BaseModel):
    mensagem: str
    telefone: str
    enviado: bool
    alerta_id: Optional[int] = None


class AlertaOut(BaseModel):
    id: int
    os_id: Optional[int] = None
    tipo_alerta: str
    telefone: str
    template_name: str
    mensagem: Optional[str] = None
    status: str
    retry_count: int
    created_at: datetime
    sent_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


LoginResponse.model_rebuild()
