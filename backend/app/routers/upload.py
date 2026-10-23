"""Upload de anexos da OS (async)."""
import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..dependencies import check_filial_access, get_current_user
from ..models import AnexosOs, AuditoriaOs, OrdemServico, User
from ..schemas import AnexoOut

router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED_MIMES = {
    "image/jpeg", "image/png", "image/webp", "image/heic",
    "application/pdf",
}
TIPOS_VALIDOS = {
    "foto_hodometro", "foto_problema", "foto_pneu",
    "nf", "orcamento", "comprovante_pagamento",
}


def _save_file(file: UploadFile, os_id: int) -> tuple[str, str, int]:
    upload_dir = Path(settings.UPLOAD_DIR) / str(os_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if file.filename else "bin"
    safe_name = f"{uuid.uuid4().hex[:12]}.{ext}"
    dest = upload_dir / safe_name
    h = hashlib.sha256()
    total = 0
    with dest.open("wb") as f:
        while True:
            chunk = file.file.read(64 * 1024)
            if not chunk:
                break
            h.update(chunk)
            f.write(chunk)
            total += len(chunk)
    return str(dest.relative_to(settings.UPLOAD_DIR)).replace("\\", "/"), h.hexdigest(), total


@router.post("/os/{os_id}/anexos", response_model=AnexoOut, status_code=201)
async def upload_anexo(
    os_id: int,
    tipo: str = Form(...),
    posicao_pneu: str = Form(default=None),
    substituir_nf: bool = Form(default=False),
    arquivo: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    os = await db.get(OrdemServico, os_id)
    if not os or os.deleted_at is not None:
        raise HTTPException(status_code=404, detail="OS não encontrada")
    if not check_filial_access(user, os.filial_id):
        raise HTTPException(status_code=403)

    if tipo not in TIPOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Tipo inválido: {tipo}")

    if arquivo.content_type not in ALLOWED_MIMES:
        raise HTTPException(
            status_code=400,
            detail=f"MIME não permitido: {arquivo.content_type}",
        )

    # "Substituir NF": a anterior sai (exclusão suave) junto com a gravação da nova. Valida ANTES
    # de salvar o arquivo, para uma recusa não deixar arquivo órfão no disco.
    antigas = []
    if tipo == "nf" and substituir_nf:
        if os.status in ("encerrada", "cancelada"):
            raise HTTPException(409, "OS já finalizada — não dá mais para substituir a NF")
        antigas = (await db.execute(select(AnexosOs).where(
            AnexosOs.os_id == os_id, AnexosOs.tipo == "nf", AnexosOs.excluido_em.is_(None),
        ))).scalars().all()
        for velha in antigas:
            if not await _pode_excluir(db, user, os, velha):
                raise HTTPException(403, "Só o gestor ou quem enviou a NF pode substituí-la")

    limite_mb = (
        settings.MAX_UPLOAD_MB_FOTO
        if tipo != "nf" else settings.MAX_UPLOAD_MB_DOC
    )
    rel_path, file_hash, size = _save_file(arquivo, os_id)
    if size > limite_mb * 1024 * 1024:
        try:
            (Path(settings.UPLOAD_DIR) / rel_path).unlink()
        except Exception:
            pass
        raise HTTPException(status_code=413, detail=f"Arquivo excede {limite_mb}MB")

    if antigas:
        for velha in antigas:
            await _excluir_suave(db, user, os, velha, "NF substituída por uma nova")

    anexo = AnexosOs(
        os_id=os_id, tipo=tipo,
        posicao_pneu=posicao_pneu if tipo == "foto_pneu" else None,
        arquivo_url=f"/uploads/{rel_path}",
        file_hash=file_hash, size_bytes=size,
        mime_type=arquivo.content_type,
        filename_original=arquivo.filename,
        uploaded_by=user.id,
    )
    db.add(anexo)
    await db.commit()
    await db.refresh(anexo)
    return anexo


async def _pode_excluir(db: AsyncSession, user: User, os: OrdemServico, anexo: AnexosOs) -> bool:
    """Gestor (admin/aprovador/filial_responsavel da filial da OS) exclui qualquer anexo;
    os demais só o que eles mesmos enviaram."""
    from ..service import _is_gestor
    return anexo.uploaded_by == user.id or await _is_gestor(db, user, os.filial_id)


async def _excluir_suave(db: AsyncSession, user: User, os: OrdemServico, a: AnexosOs, motivo: str) -> None:
    a.excluido_em = datetime.now(timezone.utc)
    a.excluido_por = user.id
    db.add(AuditoriaOs(
        os_id=os.id, operacao="anexo:excluido", user_id=user.id, filial_id=os.filial_id,
        motivo=motivo,
        before_data={"anexo_id": a.id, "tipo": a.tipo, "arquivo": a.arquivo_url, "enviado_por": a.uploaded_by},
    ))


@router.delete("/os/{os_id}/anexos/{anexo_id}")
async def delete_anexo(
    os_id: int, anexo_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Exclusão SUAVE (#0269): foto/NF subida por engano some da tela e das contagens, o arquivo
    fica no disco e a auditoria registra quem excluiu. OS encerrada/cancelada não aceita."""
    a = (await db.execute(select(AnexosOs).where(
        AnexosOs.id == anexo_id, AnexosOs.os_id == os_id, AnexosOs.excluido_em.is_(None),
    ))).scalar_one_or_none()
    if not a:
        raise HTTPException(404, "Anexo não encontrado")
    os = await db.get(OrdemServico, os_id)
    if not os or os.deleted_at is not None or not check_filial_access(user, os.filial_id):
        raise HTTPException(403)
    if os.status in ("encerrada", "cancelada"):
        raise HTTPException(409, "OS já finalizada — não dá mais para excluir anexo")
    if not await _pode_excluir(db, user, os, a):
        raise HTTPException(403, "Só o gestor ou quem enviou o anexo pode excluí-lo")
    await _excluir_suave(db, user, os, a, "Excluído pelo usuário")
    await db.commit()
    return {"ok": True}
