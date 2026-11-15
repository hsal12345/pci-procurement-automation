"""Real-time progress tracker and SSE broadcaster for document extraction & AI mapping."""
import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional, Set


STAGE_ORDER = [
    ("UPLOAD", 1, "Mengunggah Berkas"),
    ("EXTRACT_VALIDATE", 2, "Ekstraksi Konten & Konteks"),
    ("PREPARE_CONTEXT", 3, "Sanitasi PII & Pengemasan Konteks AI"),
    ("LLM_INFERENCE", 4, "Pemetaan Cerdas oleh LLM"),
    ("FINALIZE", 5, "Validasi Skema & Heuristik Akhir"),
]
STAGE_META = {sid: (idx, title) for sid, idx, title in STAGE_ORDER}

TERMINAL_STATUSES = {"COMPLETED", "AMBIGUOUS", "FALLBACK", "FAILED"}


class ImportProgressTracker:
    """In-memory pub/sub progress store per import_id with SSE streaming support."""

    def __init__(self) -> None:
        self._states: Dict[str, Dict[str, Any]] = {}
        self._started_at: Dict[str, float] = {}
        self._subscribers: Dict[str, Set[asyncio.Queue]] = {}

    def start_run(
        self,
        import_id: str,
        *,
        source_format: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        runtime_mode: Optional[str] = None,
        reset_events: bool = False,
    ) -> Dict[str, Any]:
        """Initializes or resets timing for a new analysis run on an import."""
        key = str(import_id)
        now_mono = time.monotonic()
        self._started_at[key] = now_mono
        existing = self._states.get(key)
        events: List[Dict[str, Any]] = [] if (reset_events or not existing) else list(existing.get("events", []))
        state = {
            "import_id": key,
            "stage": "EXTRACT_VALIDATE",
            "stage_index": 2,
            "total_stages": len(STAGE_ORDER),
            "percent": 15,
            "label": STAGE_META["EXTRACT_VALIDATE"][1],
            "detail": "Menyiapkan alur ekstraksi & pemetaan AI...",
            "status": "RUNNING",
            "source_format": source_format or (existing or {}).get("source_format"),
            "provider": provider or (existing or {}).get("provider"),
            "model": model or (existing or {}).get("model"),
            "runtime_mode": runtime_mode or (existing or {}).get("runtime_mode"),
            "extracted_stats": (existing or {}).get("extracted_stats") or {},
            "elapsed_ms": 0,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "events": events,
            "result": None,
            "error": None,
        }
        self._states[key] = state
        return dict(state)

    def emit(
        self,
        import_id: str,
        *,
        stage: str,
        percent: int,
        detail: str,
        label: Optional[str] = None,
        status: str = "RUNNING",
        source_format: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        runtime_mode: Optional[str] = None,
        extracted_stats: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Updates current progress state for import_id and notifies active SSE subscribers."""
        key = str(import_id)
        if key not in self._started_at:
            self._started_at[key] = time.monotonic()

        prev = self._states.get(key, {})
        stage_idx, default_label = STAGE_META.get(stage, (1, stage))
        elapsed_ms = int((time.monotonic() - self._started_at[key]) * 1000)
        now_iso = datetime.now(timezone.utc).isoformat()

        events: List[Dict[str, Any]] = list(prev.get("events", []))
        new_event = {
            "timestamp": now_iso,
            "elapsed_ms": elapsed_ms,
            "stage": stage,
            "percent": max(0, min(100, int(percent))),
            "label": label or default_label,
            "detail": detail,
            "status": status,
        }
        # Avoid spamming identical consecutive events
        if not events or (
            events[-1].get("stage") != new_event["stage"]
            or events[-1].get("detail") != new_event["detail"]
            or events[-1].get("status") != new_event["status"]
        ):
            events.append(new_event)
        events = events[-25:]

        merged_stats = dict(prev.get("extracted_stats") or {})
        if extracted_stats:
            merged_stats.update(extracted_stats)

        state = {
            "import_id": key,
            "stage": stage,
            "stage_index": stage_idx,
            "total_stages": len(STAGE_ORDER),
            "percent": max(0, min(100, int(percent))),
            "label": label or default_label,
            "detail": detail,
            "status": status,
            "source_format": source_format or prev.get("source_format"),
            "provider": provider or prev.get("provider"),
            "model": model or prev.get("model"),
            "runtime_mode": runtime_mode or prev.get("runtime_mode"),
            "extracted_stats": merged_stats,
            "elapsed_ms": elapsed_ms,
            "updated_at": now_iso,
            "events": events,
            "result": result if result is not None else prev.get("result"),
            "error": error if error is not None else prev.get("error"),
        }
        self._states[key] = state

        for queue in list(self._subscribers.get(key, set())):
            try:
                queue.put_nowait(dict(state))
            except asyncio.QueueFull:
                pass

        return dict(state)

    def get_state(self, import_id: str, fallback_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        key = str(import_id)
        if key in self._states:
            state = dict(self._states[key])
            if state.get("status") == "RUNNING" and key in self._started_at:
                state["elapsed_ms"] = int((time.monotonic() - self._started_at[key]) * 1000)
            return state
        if fallback_meta and isinstance(fallback_meta.get("progress"), dict):
            return dict(fallback_meta["progress"])
        return {
            "import_id": key,
            "stage": "UPLOAD",
            "stage_index": 1,
            "total_stages": len(STAGE_ORDER),
            "percent": 0,
            "label": "Menunggu Proses",
            "detail": "Belum ada proses AI yang berjalan untuk berkas ini.",
            "status": "IDLE",
            "source_format": (fallback_meta or {}).get("source_format"),
            "extracted_stats": (fallback_meta or {}).get("extraction_stats") or {},
            "elapsed_ms": 0,
            "events": [],
        }

    async def subscribe_sse(
        self,
        import_id: str,
        fallback_meta: Optional[Dict[str, Any]] = None,
        timeout_seconds: float = 180.0,
    ) -> AsyncIterator[str]:
        """Yields Server-Sent Events lines until terminal status or timeout."""
        key = str(import_id)
        queue: asyncio.Queue = asyncio.Queue(maxsize=64)
        self._subscribers.setdefault(key, set()).add(queue)
        deadline = time.monotonic() + timeout_seconds

        try:
            initial = self.get_state(key, fallback_meta=fallback_meta)
            yield f"event: progress\ndata: {json.dumps(initial, ensure_ascii=False)}\n\n"
            if initial.get("status") in TERMINAL_STATUSES:
                return

            while time.monotonic() < deadline:
                try:
                    update = await asyncio.wait_for(queue.get(), timeout=10.0)
                    yield f"event: progress\ndata: {json.dumps(update, ensure_ascii=False)}\n\n"
                    if update.get("status") in TERMINAL_STATUSES:
                        return
                except asyncio.TimeoutError:
                    # Emit live elapsed ping so UI timer/heartbeat stays alive
                    current = self.get_state(key, fallback_meta=fallback_meta)
                    yield f"event: ping\ndata: {json.dumps({'elapsed_ms': current.get('elapsed_ms', 0), 'status': current.get('status')})}\n\n"
                    if current.get("status") in TERMINAL_STATUSES:
                        yield f"event: progress\ndata: {json.dumps(current, ensure_ascii=False)}\n\n"
                        return
        finally:
            subs = self._subscribers.get(key)
            if subs and queue in subs:
                subs.discard(queue)
                if not subs:
                    self._subscribers.pop(key, None)


import_progress_tracker = ImportProgressTracker()
