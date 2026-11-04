import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.ai import (
    SystemKnowledgeChatRequest,
    SystemKnowledgeChatResponse,
    SystemKnowledgeChatResult,
    SystemKnowledgeInfoResponse,
    SystemKnowledgeRouteItem,
)
from app.services.ai.adapter import get_ai_adapter, MockAIAdapter
from app.services.ai.budget_guard import AIBudgetGuard
from app.services.ai.runtime_manager import runtime_manager

logger = logging.getLogger(__name__)

KNOWLEDGE_FILENAME = "system_knowledge.md"


class SystemKnowledgeService:
    """Service to load, cache, and serve system knowledge context from Markdown (.md)
    and guide users through the PCI Procurement & SPJ system navigation and features.
    """

    _cached_content: Optional[str] = None
    _cached_mtime: float = 0.0
    _cached_sections: List[str] = []

    @classmethod
    def get_knowledge_file_path(cls) -> Path:
        """Finds the absolute path to system_knowledge.md."""
        # 1. Look in backend/app/knowledge/
        current_dir = Path(__file__).resolve().parent
        candidate_1 = current_dir.parent / "knowledge" / KNOWLEDGE_FILENAME
        if candidate_1.exists():
            return candidate_1

        # 2. Look in /app/app/knowledge/ (inside Docker container)
        candidate_2 = Path("/app/app/knowledge") / KNOWLEDGE_FILENAME
        if candidate_2.exists():
            return candidate_2

        # 3. Look in root or fallback paths
        candidate_3 = Path.cwd() / "app" / "knowledge" / KNOWLEDGE_FILENAME
        if candidate_3.exists():
            return candidate_3

        # Default fallback
        return candidate_1

    @classmethod
    def load_knowledge_content(cls) -> Tuple[str, List[str], datetime, int]:
        """Loads and caches the markdown knowledge file text, refreshing if file on disk changed."""
        path = cls.get_knowledge_file_path()
        if not path.exists():
            logger.warning(f"Knowledge file not found at {path}, generating emergency context.")
            cls._cached_content = (
                "# PANDUAN PENGETAHUAN SISTEM PCI PROCUREMENT\n"
                "Sistem Otomasi Pengadaan Barang & Jasa CV Pustaka Cemerlang Indonesia."
            )
            cls._cached_sections = ["1. Gambaran Umum Sistem"]
            return cls._cached_content, cls._cached_sections, datetime.utcnow(), len(cls._cached_content)

        mtime = path.stat().st_mtime
        if cls._cached_content is None or mtime > cls._cached_mtime:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                cls._cached_content = content
                cls._cached_mtime = mtime

                # Extract section titles from ## headings
                sections = []
                for line in content.splitlines():
                    match = re.match(r"^##\s+(.+)$", line.strip())
                    if match:
                        sections.append(match.group(1).strip())
                cls._cached_sections = sections
                logger.info(f"Loaded System Knowledge context from {path} ({len(content)} chars, {len(sections)} sections).")
            except Exception as e:
                logger.error(f"Error reading knowledge file at {path}: {e}")
                if cls._cached_content is None:
                    cls._cached_content = "Sistem Pengadaan CV Pustaka Cemerlang Indonesia."
                    cls._cached_sections = []

        last_updated = datetime.fromtimestamp(cls._cached_mtime)
        return cls._cached_content, cls._cached_sections, last_updated, len(cls._cached_content.encode("utf-8"))

    @classmethod
    def get_info(cls) -> SystemKnowledgeInfoResponse:
        """Returns metadata and raw markdown content of the loaded system knowledge."""
        content, sections, last_updated, size_bytes = cls.load_knowledge_content()
        return SystemKnowledgeInfoResponse(
            title="Sistem Otomasi Pengadaan & SPJ - CV Pustaka Cemerlang Indonesia",
            filename=KNOWLEDGE_FILENAME,
            last_updated=last_updated.isoformat(),
            content=content,
            size_bytes=size_bytes,
            sections=sections,
        )

    @classmethod
    def build_system_prompt(cls) -> str:
        """Constructs the strict system prompt injecting the system knowledge markdown context."""
        content, _, _, _ = cls.load_knowledge_content()

        system_prompt = (
            "You are the official PCI System Knowledge & Navigation Guide Assistant for "
            "CV Pustaka Cemerlang Indonesia (PCI Procurement & SPJ Automation System).\n\n"
            "STRICT OPERATIONAL GUARDRAILS & DIRECTIVES:\n"
            "1. SCOPE RESTRICTION: You must ONLY answer questions directly related to this procurement application, "
            "its menus, pages, UI tabs, roles (Administration, Logistics, Finance Director, Sysadmin), 13 SPJ documents "
            "(D01-D13), validation business rules (BR01-BR15), workflow status transitions, and step-by-step navigation instructions.\n"
            "2. OUT-OF-SCOPE INQUIRIES: If the user asks about general trivia, programming code outside this system, "
            "cooking recipes, politics, general weather, or ANY topic not covered by this system knowledge base, "
            "you MUST politely decline and steer them back to this procurement system.\n"
            "3. NAVIGATION FIRST: Always recommend exact internal system routes (e.g. /packages, /imports, /schools, /companies, "
            "/packages?filter=under_review, /packages?tab=documents, /ai/usage, /users) and populate the `suggested_routes` list.\n"
            "4. TONE & LANGUAGE: Respond in polite, structured, professional Bahasa Indonesia using GitHub Flavored Markdown "
            "(bold keywords, bullet points, numbered steps).\n"
            "5. OUTPUT FORMAT: Respond strictly in the required JSON schema matching SystemKnowledgeChatResult.\n\n"
            "=================== SYSTEM KNOWLEDGE BASE (CONTEXT) ===================\n"
            f"{content}\n"
            "======================================================================\n"
        )
        return system_prompt

    @classmethod
    def build_user_prompt(cls, message: str, history: List[Any]) -> str:
        """Formats the conversation history and current user inquiry."""
        history_text = ""
        if history:
            history_lines = []
            for item in history[-6:]:  # Keep recent turns
                role = "User" if getattr(item, "role", "user") == "user" else "Assistant"
                content = getattr(item, "content", "")
                history_lines.append(f"{role}: {content}")
            history_text = "Recent conversation context:\n" + "\n".join(history_lines) + "\n\n"

        return f"{history_text}User Question: {message}\n\nPlease provide a comprehensive, step-by-step guidance conforming to the system knowledge base."

    @classmethod
    async def chat(
        cls,
        db: AsyncSession,
        request: SystemKnowledgeChatRequest
    ) -> Tuple[Optional[SystemKnowledgeChatResponse], str, Optional[str]]:
        """Handles a chat message against the system knowledge context with guardrails and token budget tracking."""
        system_prompt = cls.build_system_prompt()
        user_prompt = cls.build_user_prompt(request.message, request.history or [])

        adapter = get_ai_adapter()
        mock_adapter = MockAIAdapter()
        cfg = runtime_manager.get_config()

        async def _run_task():
            return await adapter.complete_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=SystemKnowledgeChatResult
            )

        async def _fallback_task():
            return await mock_adapter.complete_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=SystemKnowledgeChatResult
            )

        result, status, err_msg = await AIBudgetGuard.execute_guarded(
            db=db,
            task_type="SYSTEM_KNOWLEDGE_CHAT",
            execute_fn=_run_task,
            fallback_fn=_fallback_task
        )

        if result is None:
            # Emergency mock response if budget guard failed completely
            emergency_reply = (
                "Mohon maaf, layanan kecerdasan buatan sedang tidak dapat dijangkau. "
                "Anda dapat membuka menu **Paket Pengadaan** di `/packages` atau membaca dokumentasi sistem."
            )
            return (
                SystemKnowledgeChatResponse(
                    reply=emergency_reply,
                    suggested_routes=[
                        SystemKnowledgeRouteItem(
                            title="Paket Pengadaan",
                            path="/packages",
                            description="Kelola dan buat transaksi pengadaan SD."
                        )
                    ],
                    suggested_questions=[
                        "Bagaimana cara membuat paket pengadaan baru?",
                        "Apa peran Direktur Keuangan dalam persetujuan paket?"
                    ],
                    runtime_mode=cfg.runtime_mode,
                    provider=cfg.provider,
                    model=cfg.model,
                    tokens_used=0,
                    latency_ms=0,
                ),
                status,
                err_msg,
            )

        # Build final response
        chat_result: SystemKnowledgeChatResult = result
        return (
            SystemKnowledgeChatResponse(
                reply=chat_result.reply,
                suggested_routes=chat_result.suggested_routes,
                suggested_questions=chat_result.suggested_questions,
                runtime_mode=cfg.runtime_mode,
                provider=cfg.provider,
                model=cfg.model,
                tokens_used=0,
                latency_ms=0,
            ),
            status,
            err_msg,
        )


system_knowledge_service = SystemKnowledgeService()

