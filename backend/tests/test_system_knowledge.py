import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import async_engine
from app.services.ai.system_knowledge_service import system_knowledge_service
from app.schemas.ai import SystemKnowledgeChatRequest


@pytest.fixture(autouse=True)
async def dispose_engine_after_test():
    yield
    await async_engine.dispose()


@pytest.mark.asyncio
async def test_system_knowledge_file_loading():
    """Verifies that system_knowledge.md is correctly read, parsed, and cached."""
    info = system_knowledge_service.get_info()
    assert info.title == "Sistem Otomasi Pengadaan & SPJ - CV Pustaka Cemerlang Indonesia"
    assert info.filename == "system_knowledge.md"
    assert info.size_bytes > 5000
    assert len(info.sections) >= 5
    assert "1. Identitas & Gambaran Umum Sistem" in info.sections
    assert "2. Peta Panduan Navigasi Sistem (Navigation Guide & Menus)" in info.sections


@pytest.mark.asyncio
async def test_system_prompt_builder():
    """Verifies strict boundary directives and context injection in system prompt."""
    prompt = system_knowledge_service.build_system_prompt()
    assert "STRICT OPERATIONAL GUARDRAILS & DIRECTIVES" in prompt
    assert "You must ONLY answer questions directly related to this procurement application" in prompt
    assert "PANDUAN PENGETAHUAN SISTEM (SYSTEM KNOWLEDGE BASE)" in prompt
    assert "/packages" in prompt
    assert "D01" in prompt


@pytest.mark.asyncio
async def test_knowledge_api_endpoint():
    """Verifies GET /api/v1/ai/knowledge returns valid schema and content."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/ai/knowledge")
        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"] == "system_knowledge.md"
        assert len(data["content"]) > 1000
        assert len(data["sections"]) >= 5


@pytest.mark.asyncio
async def test_knowledge_chat_endpoint_navigation():
    """Verifies POST /api/v1/ai/knowledge/chat answers navigation questions with routes."""
    headers = {"X-User-Role": "ADMINISTRATION"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "message": "Bagaimana cara mengimpor berkas Excel transaksi?",
            "history": []
        }
        resp = await client.post("/api/v1/ai/knowledge/chat", json=payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "reply" in data
        assert len(data["reply"]) > 50
        assert "suggested_routes" in data
        assert any(r["path"] == "/imports" for r in data["suggested_routes"])
        assert len(data["suggested_questions"]) > 0


@pytest.mark.asyncio
async def test_knowledge_chat_endpoint_off_topic_guardrail():
    """Verifies that off-topic questions are politely rejected according to system guardrails."""
    headers = {"X-User-Role": "ADMINISTRATION"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "message": "Bagikan resep memasak rendang daging padang lezat",
            "history": []
        }
        resp = await client.post("/api/v1/ai/knowledge/chat", json=payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "Mohon maaf" in data["reply"]
        assert "hanya berwenang" in data["reply"]
