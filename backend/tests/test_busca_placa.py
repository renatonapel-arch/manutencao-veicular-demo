"""#0305: busca da lista de OS acha pela placa (com/sem hífen, minúscula), modelo ou problema."""
import uuid

import pytest

from app.models import OrdemServico, VeiculoSnapshot
from app.routers import ordem_servico


async def _base(db, admin):
    db.add_all([
        VeiculoSnapshot(id=1, veiculo_patrimonial_id=1, placa="BEE2A87", modelo="CG 160 FAN", tipo="moto", km_atual=1, filial_id=1, ativo=True),
        VeiculoSnapshot(id=2, veiculo_patrimonial_id=2, placa="RPL-1B57", modelo="Strada", tipo="carro", km_atual=1, filial_id=2, ativo=True),
    ])
    await db.flush()
    for vid, fil, desc in ((1, 1, "Troca de lona de freio"), (2, 2, "pneu furado")):
        db.add(OrdemServico(request_id=uuid.uuid4(), veiculo_id=vid, filial_id=fil, aberto_por_user_id=admin.id,
                            tipo_os="corretiva_manual", km_veiculo=1, status="aberta", descricao_problema=desc))
    await db.commit()


async def _busca(db, user, q):
    r = await ordem_servico.list_os(filial_id=None, status=None, tipo=None, categoria=None, veiculo_id=None,
                                    oficina_id=None, q=q, limit=20, offset=0, user=user, db=db)
    return sorted(o.veiculo_placa for o in r.data)


@pytest.mark.parametrize("q,placas", [
    ("BEE2A87", ["BEE2A87"]), ("bee-2a87", ["BEE2A87"]), ("2a8", ["BEE2A87"]),
    ("rpl1b57", ["RPL-1B57"]), ("RPL-1B57", ["RPL-1B57"]),
    ("strada", ["RPL-1B57"]), ("freio", ["BEE2A87"]), ("ZZZ9Z99", []),
])
async def test_busca(db, admin_user, q, placas):
    await _base(db, admin_user)
    assert await _busca(db, admin_user, q) == placas


async def test_filial_restrita_continua_so_nas_suas(db, admin_user, responsavel_user):
    await _base(db, admin_user)
    assert await _busca(db, responsavel_user, "rpl1b57") == []
    assert await _busca(db, responsavel_user, "bee2a87") == ["BEE2A87"]
