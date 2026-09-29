"""run_async_job (#0220): job do APScheduler roda em loop próprio com engine
descartável. Guarda as invariantes que evitam vazar conexão no Postgres
(engine global + asyncio.run() em thread deixava 1 conexão presa a cada 2
execuções e derrubou o módulo com 100/100 conexões).

Testes SÍNCRONOS de propósito: run_async_job usa asyncio.run(), que não pode
rodar dentro de um loop já ativo.
"""
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.pool import NullPool

from app import database
from app.jobs import sync_veiculos as job_sync


@pytest.fixture
def spy(monkeypatch):
    created, disposed = [], []
    real_create = database.create_async_engine
    real_dispose = AsyncEngine.dispose

    def fake_create(*a, **k):
        eng = real_create(*a, **k)
        created.append(eng)
        return eng

    async def spy_dispose(self, *a, **k):
        disposed.append(self)
        return await real_dispose(self, *a, **k)

    monkeypatch.setattr(database, "create_async_engine", fake_create)
    monkeypatch.setattr(AsyncEngine, "dispose", spy_dispose)
    return created, disposed


def test_devolve_resultado_com_engine_descartavel(spy):
    created, disposed = spy

    async def fn(db):
        return (await db.execute(text("select 41 + 1"))).scalar_one()

    assert database.run_async_job(fn) == 42
    assert len(created) == 1
    # NullPool: nenhuma conexão sobrevive ao fim do job
    assert isinstance(created[0].sync_engine.pool, NullPool)
    # engine criado É o engine descartado (nada fica pra trás)
    assert disposed == created


def test_engine_e_descartado_mesmo_quando_o_job_falha(spy):
    created, disposed = spy

    async def fn(db):
        raise RuntimeError("falha do job")

    with pytest.raises(RuntimeError, match="falha do job"):
        database.run_async_job(fn)
    assert len(created) == 1 and disposed == created


def test_cada_execucao_cria_seu_proprio_engine(spy):
    created, disposed = spy

    async def fn(db):
        await db.execute(text("select 1"))

    for _ in range(3):
        database.run_async_job(fn)
    assert len(created) == 3 and len(disposed) == 3
    assert len({id(e) for e in created}) == 3  # nunca reaproveita engine entre execuções


def test_sync_veiculos_job_nao_propaga_erro(monkeypatch):
    """Job que falha não pode derrubar a thread do scheduler."""
    def boom(fn):
        raise ConnectionError("banco fora")

    monkeypatch.setattr(job_sync, "run_async_job", boom)
    assert job_sync.sync_veiculos_job() is None  # engole e loga, não levanta
