import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import async_engine
from app.services.ai.runtime_manager import runtime_manager


@pytest.fixture(autouse=True)
async def cleanup_loop():
    yield
    await async_engine.dispose()


@pytest.mark.asyncio
async def test_ai_runtime_configuration_and_toggle():
    transport = ASGITransport(app=app)
    headers = {
        "X-User-Role": "SYSTEM_ADMINISTRATOR",
        "X-Actor-Name": "Administrator Sistem"
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET /api/v1/ai/config
        get_res = await client.get("/api/v1/ai/config", headers=headers)
        assert get_res.status_code == 200
        data = get_res.json()
        assert "runtime_mode" in data
        assert "provider" in data
        assert "available_models" in data

        # 2. PUT /api/v1/ai/config -> Switch to API mode
        put_api_res = await client.put(
            "/api/v1/ai/config",
            headers=headers,
            json={
                "runtime_mode": "api",
                "provider": "gemini",
                "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
                "model": "gemini-2.0-flash",
                "api_key": "AIzaSyTestKey123456789",
                "timeout_seconds": 25,
                "monthly_budget_usd": 15.0,
                "auto_fallback_to_local": True,
                "ai_enabled": True
            }
        )
        assert put_api_res.status_code == 200
        api_data = put_api_res.json()
        assert api_data["runtime_mode"] == "api"
        assert api_data["provider"] == "gemini"
        assert api_data["model"] == "gemini-2.0-flash"
        assert api_data["has_api_key"] is True
        assert "..." in api_data["api_key_masked"]

        # 3. PUT /api/v1/ai/config -> Switch back to Local mode
        put_local_res = await client.put(
            "/api/v1/ai/config",
            headers=headers,
            json={
                "runtime_mode": "local",
                "provider": "mock",
                "model": "mock-rule-engine",
                "auto_fallback_to_local": True
            }
        )
        assert put_local_res.status_code == 200
        local_data = put_local_res.json()
        assert local_data["runtime_mode"] == "local"
        assert local_data["provider"] == "mock"


@pytest.mark.asyncio
async def test_ai_test_connection_endpoint():
    transport = ASGITransport(app=app)
    headers = {
        "X-User-Role": "ADMINISTRATION",
        "X-Actor-Name": "Staf Administrasi"
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test connection for local mock engine
        res = await client.post(
            "/api/v1/ai/test-connection",
            headers=headers,
            json={
                "runtime_mode": "local",
                "provider": "mock",
                "model": "mock-rule-engine"
            }
        )
        assert res.status_code == 200
        conn_data = res.json()
        assert conn_data["status"] == "ONLINE"
        assert conn_data["runtime_mode"] == "local"
        assert conn_data["latency_ms"] >= 0
        assert "siap dan aktif" in conn_data["message"].lower()


@pytest.mark.asyncio
async def test_ai_playground_and_logs():
    transport = ASGITransport(app=app)
    headers = {
        "X-User-Role": "ADMINISTRATION",
        "X-Actor-Name": "Staf Administrasi"
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Test discrepancy playground
        play_res = await client.post(
            "/api/v1/ai/playground/test",
            headers=headers,
            json={
                "test_type": "DISCREPANCY",
                "text_a": "Pembersih Porselen Botol 1L",
                "text_b": "Porstex Botol 1000ml"
            }
        )
        assert play_res.status_code == 200
        pdata = play_res.json()
        assert pdata["test_type"] == "DISCREPANCY"
        assert "output" in pdata
        assert "discrepancy_type" in pdata["output"]

        # 2. Test mapping playground
        map_res = await client.post(
            "/api/v1/ai/playground/test",
            headers=headers,
            json={
                "test_type": "MAPPING",
                "sample_headers": ["No", "Nama Buku", "Spesifikasi", "Vol", "Satuan", "Harga", "Jumlah"]
            }
        )
        assert map_res.status_code == 200
        mdata = map_res.json()
        assert mdata["test_type"] == "MAPPING"
        assert mdata["output"]["confidence_score"] > 0.0

        # 3. Test logs retrieval
        log_res = await client.get("/api/v1/ai/logs?limit=10", headers=headers)
        assert log_res.status_code == 200
        logs = log_res.json()
        assert isinstance(logs, list)
        assert len(logs) >= 2
