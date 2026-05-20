"""Upload de anexos da OS (foto + NF)."""
import hashlib
import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..dependencies import check_filial_access, get_current_user
from ..models import AnexosOs, OrdemServico, TipoAnexoEnum, User
from ..schemas import AnexoOut

router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED_MIMES = {
    "image/jpeg", "image/png", "image/webp", "image/heic",
    "application/pdf",
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
def upload_anexo(
    os_id: int,
    tipo: str = Form(...),
    arquivo: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    os = db.query(OrdemServico).filter(OrdemServico.id == os_id).first()
    if not os:
        raise HTTPException(status_code=404, detail="OS não encontrada")
    if not check_filial_access(user, os.filial_id):
        raise HTTPException(status_code=403)

    try:
        tipo_enum = TipoAnexoEnum(tipo)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Tipo inválido: {tipo}")

    if arquivo.content_type not in ALLOWED_MIMES:
        raise HTTPException(status_code=400, detail=f"MIME não permitido: {arquivo.content_type}")

    limite_mb = settings.MAX_UPLOAD_MB_FOTO if tipo_enum != TipoAnexoEnum.nf else settings.MAX_UPLOAD_MB_DOC
    rel_path, file_hash, size = _save_file(arquivo, os_id)
    if size > limite_mb * 1024 * 1024:
        # rollback do arquivo
        try:
            (Path(settings.UPLOAD_DIR) / rel_path).unlink()
        except Exception:
            pass
        raise HTTPException(status_code=413, detail=f"Arquivo excede {limite_mb}MB")

    anexo = AnexosOs(
        os_id=os_id, tipo=tipo_enum,
        arquivo_url=f"/uploads/{rel_path}",
        file_hash=file_hash, size_bytes=size,
        mime_type=arquivo.content_type,
        filename_original=arquivo.filename,
        uploaded_by=user.id,
    )
    db.add(anexo)
    db.commit()
    db.refresh(anexo)
    return anexo


@router.delete("/os/{os_id}/anexos/{anexo_id}")
def delete_anexo(os_id: int, anexo_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = db.query(AnexosOs).filter(AnexosOs.id == anexo_id, AnexosOs.os_id == os_id).first()
    if not a:
        raise HTTPException(404)
    os = db.query(OrdemServico).filter(OrdemServico.id == os_id).first()
    if not check_filial_access(user, os.filial_id):
        raise HTTPException(403)
    db.delete(a)
    db.commit()
    return {"ok": True}
