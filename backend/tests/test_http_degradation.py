"""Testes de degradação HTTP — Frota/Troca-Óleo offline não crasham o módulo.

Mockamos httpx.AsyncClient com respostas simuladas (200/503/timeout).
"""
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.integrations import oleo_client, patrimonial_client


async def test_frota_503_retorna_cache_ou_vazio():
    """Frota devolve 503 → cliente retorna lista vazia (não crasha)."""
    # Limpa cache global antes
    patrimonial_client._VEIC_CACHE["data"] = None
    patrimonial_client._VEIC_CACHE["ts"] = 0.0

    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_response.json = MagicMock(return_value={})

    async def _fake_get(*args, **kwargs):
        return mock_response

    with patch.object(httpx.AsyncClient, "get", new=AsyncMock(side_effect=_fake_get)):
        result = await patrimonial_client.fetch_veiculos_da_frota()
        assert result == []


async def test_frota_timeout_retorna_cache_ou_vazio():
    """Frota timeout → cliente retorna lista vazia (não crasha)."""
    patrimonial_client._VEIC_CACHE["data"] = None
    patrimonial_client._VEIC_CACHE["ts"] = 0.0

    async def _fake_get(*args, **kwargs):
        raise httpx.TimeoutException("timeout")

    with patch.object(httpx.AsyncClient, "get", new=AsyncMock(side_effect=_fake_get)):
        result = await patrimonial_client.fetch_veiculos_da_frota()
        assert result == []


async def test_frota_200_popula_cache():
    """Frota 200 → payload chega e cache é populado."""
    patrimonial_client._VEIC_CACHE["data"] = None
    patrimonial_client._VEIC_CACHE["ts"] = 0.0

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json = MagicMock(return_value={
        "vehicles": [
            {"id": "abc123", "placa": "AAA1B23", "modelo": "Test",
             "filial_id": 100, "km_atual": 500, "ativo": True},
        ]
    })

    async def _fake_get(*args, **kwargs):
        return mock_response

    with patch.object(httpx.AsyncClient, "get", new=AsyncMock(side_effect=_fake_get)):
        result = await patrimonial_client.fetch_veiculos_da_frota()
        assert len(result) == 1
        assert result[0]["placa"] == "AAA1B23"
        # Cache foi preenchido
        assert patrimonial_client._VEIC_CACHE["data"] is not None


async def test_troca_oleo_offline_nao_crasha():
    """Troca-Óleo 503 → listar_oficinas retorna lista vazia."""
    oleo_client._OFIC_CACHE["data"] = None
    oleo_client._OFIC_CACHE["ts"] = 0.0

    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_response.json = MagicMock(return_value={})

    async def _fake_get(*args, **kwargs):
        return mock_response

    with patch.object(httpx.AsyncClient, "get", new=AsyncMock(side_effect=_fake_get)):
        result = await oleo_client.listar_oficinas()
        assert result == []
