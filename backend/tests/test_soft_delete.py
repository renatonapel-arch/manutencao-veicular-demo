"""Teste soft-delete — helper _ativas filtra tudo."""
from decimal import Decimal
from datetime import datetime

import pytest
from fastapi import HTTPException

from app import service
from tests.conftest import make_os


async def test_delete_marca_deleted_at(db, admin_user, veiculo):
    os = await make_os(db, admin_user, veiculo, status="aberta")
    await service.soft_delete_os(db, os.id, admin_user, motivo="teste")

    # Refresh: deleted_at deve estar preenchido
    await db.refresh(os)
    assert os.deleted_at is not None


async def test_deletada_nao_aparece_em_get(db, admin_user, veiculo):
    os = await make_os(db, admin_user, veiculo, status="aberta")
    await service.soft_delete_os(db, os.id, admin_user)

    # get_os deve retornar None mesmo com ID válido
    result = await service.get_os(db, os.id)
    assert result is None


async def test_deletada_nao_aparece_em_listar(db, admin_user, veiculo):
    os1 = await make_os(db, admin_user, veiculo, status="aberta")
    os2 = await make_os(db, admin_user, veiculo, status="em_triagem")

    await service.soft_delete_os(db, os1.id, admin_user)

    lista = await service.listar_os(db)
    ids = [o.id for o in lista]
    assert os1.id not in ids
    assert os2.id in ids


async def test_deletada_nao_conta(db, admin_user, veiculo):
    os1 = await make_os(db, admin_user, veiculo, status="aberta")
    await make_os(db, admin_user, veiculo, status="aberta")

    total_antes = await service.contar_os(db)
    await service.soft_delete_os(db, os1.id, admin_user)
    total_depois = await service.contar_os(db)

    assert total_depois == total_antes - 1


async def test_transicionar_deletada_falha(db, admin_user, veiculo):
    """OS deletada não pode ser transicionada."""
    os = await make_os(db, admin_user, veiculo, status="aberta")
    await service.soft_delete_os(db, os.id, admin_user)

    with pytest.raises(HTTPException) as exc:
        await service.transicionar(db, os.id, "em_triagem", admin_user)
    assert exc.value.status_code == 404
