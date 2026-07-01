"""Upload de anexos da OS (async)."""
import hashlib
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..dependencies import check_filial_access, get_current_user
from ..models import AnexosOs, OrdemServico, User
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


@router.delete("/os/{os_id}/anexos/{anexo_id}")
async def delete_anexo(
    os_id: int, anexo_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AnexosOs).where(
        AnexosOs.id == anexo_id, AnexosOs.os_id == os_id,
    )
    a = (await db.execute(stmt)).scalar_one_or_none()
    if not a:
        raise HTTPException(404)
    os = await db.get(OrdemServico, os_id)
    if not os or not check_filial_access(user, os.filial_id):
        raise HTTPException(403)
    await db.delete(a)
    await db.commit()
    return {"ok": True}
