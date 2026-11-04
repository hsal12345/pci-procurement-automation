import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import httpx
from pydantic import BaseModel, Field

from app.config import settings
from app.services.ai.adapter import BaseAIAdapter, MockAIAdapter, OpenAICompatibleAdapter

logger = logging.getLogger(__name__)

CONFIG_FILE_NAME = "ai_runtime_config.json"


class AIRuntimeConfig(BaseModel):
    runtime_mode: str = Field("local", description="'api' for Cloud/External APIs, 'local' for Local LLM / Deterministic Mock")
    provider: str = Field("mock", description="gemini, openrouter, openai, ollama, mock, custom")
    base_url: str = Field("http://localhost:11434/v1", description="Effective base API URL")
    api_key: Optional[str] = Field(None, description="API Key for cloud providers")
    model: str = Field("mock-rule-engine", description="Active model name")
    timeout_seconds: int = Field(30, ge=5, le=120, description="Request timeout in seconds")
    monthly_budget_usd: float = Field(10.0, ge=0.0, description="Monthly spending limit in USD")
    auto_fallback_to_local: bool = Field(True, description="Automatically fallback to Local mock if API is down or budget exhausted")
    ai_enabled: bool = Field(True, description="Master enable/disable toggle for AI assistance")


class AIRuntimeManager:
    """Manages active AI runtime mode (API Runtime vs Local Runtime),
    dynamic provider switching, persistence, connectivity diagnostics,
    and automatic failover to local engine.
    """

    _instance: Optional["AIRuntimeManager"] = None
    _config: AIRuntimeConfig

    def __init__(self):
        self._config = self._load_initial_config()

    @classmethod
    def get_instance(cls) -> "AIRuntimeManager":
        if cls._instance is None:
            cls._instance = AIRuntimeManager()
        return cls._instance

    def _get_storage_path(self) -> Path:
        return settings.get_artifact_dir().parent / CONFIG_FILE_NAME

    def _load_initial_config(self) -> AIRuntimeConfig:
        config_path = self._get_storage_path()
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logger.info(f"Loaded persistent AI runtime config from {config_path}")
                return AIRuntimeConfig(**data)
            except Exception as e:
                logger.warning(f"Failed to read {config_path}, falling back to env settings: {e}")

        # Fallback to settings
        provider = (settings.AI_PROVIDER or "mock").lower().strip()
        runtime_mode = "api" if provider in ["gemini", "openrouter", "openai"] and settings.AI_API_KEY else "local"
        if runtime_mode == "local" and provider not in ["ollama", "mock"]:
            provider = "mock"

        base_url = settings.get_effective_ai_base_url()
        if runtime_mode == "local" and provider == "mock":
            model = "mock-rule-engine"
        else:
            model = settings.AI_MODEL or "google/gemini-2.0-flash-exp:free"

        return AIRuntimeConfig(
            runtime_mode=runtime_mode,
            provider=provider,
            base_url=base_url,
            api_key=settings.AI_API_KEY,
            model=model,
            timeout_seconds=settings.AI_REQUEST_TIMEOUT_SECONDS or 30,
            monthly_budget_usd=settings.AI_MONTHLY_BUDGET_USD or 10.0,
            auto_fallback_to_local=True,
            ai_enabled=settings.AI_ENABLED
        )

    def get_config(self) -> AIRuntimeConfig:
        return self._config

    def get_masked_config_dict(self) -> Dict[str, Any]:
        cfg = self._config.model_dump()
        raw_key = cfg.get("api_key") or ""
        if raw_key and len(raw_key) > 8:
            cfg["api_key_masked"] = f"{raw_key[:4]}...{raw_key[-4:]}"
        elif raw_key:
            cfg["api_key_masked"] = "••••••••"
        else:
            cfg["api_key_masked"] = ""
        cfg["has_api_key"] = bool(raw_key)
        return cfg

    def update_config(self, new_data: Dict[str, Any]) -> AIRuntimeConfig:
        current_dict = self._config.model_dump()

        # If user provides an empty string or 'KEEP_CURRENT' or masked for api_key, preserve existing
        if "api_key" in new_data:
            key_val = str(new_data["api_key"]).strip()
            if not key_val or "..." in key_val or "••" in key_val:
                new_data["api_key"] = current_dict.get("api_key")

        # Normalize provider & runtime_mode
        if "runtime_mode" in new_data:
            mode = str(new_data["runtime_mode"]).lower().strip()
            if mode not in ["api", "local"]:
                mode = "local"
            new_data["runtime_mode"] = mode

        # Auto-adjust default URLs and models if provider changed
        provider = str(new_data.get("provider", current_dict["provider"])).lower().strip()
        new_data["provider"] = provider

        if "base_url" not in new_data or not str(new_data.get("base_url", "")).strip():
            if provider == "gemini":
                new_data["base_url"] = "https://generativelanguage.googleapis.com/v1beta/openai"
            elif provider == "openrouter":
                new_data["base_url"] = "https://openrouter.ai/api/v1"
            elif provider == "openai":
                new_data["base_url"] = "https://api.openai.com/v1"
            elif provider == "ollama":
                new_data["base_url"] = "http://localhost:11434/v1"
            elif provider == "mock":
                new_data["base_url"] = "local://deterministic-engine"

        merged = {**current_dict, **new_data}
        self._config = AIRuntimeConfig(**merged)

        # Sync runtime settings back to global settings for consistency
        settings.AI_ENABLED = self._config.ai_enabled
        settings.AI_PROVIDER = self._config.provider
        settings.AI_MODEL = self._config.model
        settings.AI_BASE_URL = self._config.base_url
        if self._config.api_key:
            settings.AI_API_KEY = self._config.api_key
        settings.AI_MONTHLY_BUDGET_USD = self._config.monthly_budget_usd
        settings.AI_REQUEST_TIMEOUT_SECONDS = self._config.timeout_seconds

        # Persist to disk
        try:
            config_path = self._get_storage_path()
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self._config.model_dump(), f, indent=2)
            logger.info(f"AI runtime configuration persisted to {config_path}")
        except Exception as e:
            logger.error(f"Failed to persist AI runtime configuration: {e}")

        return self._config

    def get_active_adapter(self) -> BaseAIAdapter:
        """Returns the appropriate BaseAIAdapter instance based on active runtime configuration."""
        if not self._config.ai_enabled:
            return MockAIAdapter()

        if self._config.runtime_mode == "local":
            if self._config.provider == "mock":
                return MockAIAdapter()
            elif self._config.provider in ["ollama", "vllm", "custom"]:
                # Local OpenAI compatible server (Ollama, vLLM, etc.)
                resolved_url = self._resolve_local_url(self._config.base_url)
                return OpenAICompatibleAdapter(
                    api_key=self._config.api_key or "ollama",
                    base_url=resolved_url,
                    model=self._config.model,
                    timeout_seconds=self._config.timeout_seconds
                )
            return MockAIAdapter()

        # API Mode (Cloud API)
        if not self._config.api_key:
            logger.warning("API Runtime selected but no API key configured. Falling back to Mock.")
            return MockAIAdapter()

        return OpenAICompatibleAdapter(
            api_key=self._config.api_key,
            base_url=self._config.base_url,
            model=self._config.model,
            timeout_seconds=self._config.timeout_seconds
        )

    def _resolve_local_url(self, url: str) -> str:
        """Resolves localhost to host.docker.internal when running inside Docker container."""
        if not url:
            return url
        url_clean = url.strip()
        # If running inside Docker and target is localhost/127.0.0.1, check if inside container
        is_docker = Path("/.dockerenv").exists()
        if is_docker:
            if "localhost" in url_clean:
                url_clean = url_clean.replace("localhost", "host.docker.internal")
            elif "127.0.0.1" in url_clean:
                url_clean = url_clean.replace("127.0.0.1", "host.docker.internal")
        return url_clean

    async def test_connection(self, test_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Tests connectivity, authentication, and response latency for the given or active runtime."""
        target = self._config
        if test_config:
            merged = {**self._config.model_dump(), **test_config}
            target = AIRuntimeConfig(**merged)

        runtime_mode = target.runtime_mode
        provider = target.provider
        model = target.model

        start_time = time.monotonic()

        # 1. Deterministic Local Mock
        if runtime_mode == "local" and provider == "mock":
            mock_adapter = MockAIAdapter()
            latency = int((time.monotonic() - start_time) * 1000) or 5
            return {
                "status": "ONLINE",
                "latency_ms": latency,
                "runtime_mode": "local",
                "provider": "mock",
                "model": "mock-rule-engine",
                "endpoint": "local://deterministic-engine",
                "message": "Engine Aturan Deterministik Lokal siap dan aktif (100% offline, bebas biaya & instan).",
                "is_fallback": False
            }

        # 2. Local Ollama or Cloud API
        base_url = target.base_url.rstrip("/")
        if runtime_mode == "local":
            base_url = self._resolve_local_url(base_url)

        headers = {"Content-Type": "application/json"}
        if target.api_key:
            headers["Authorization"] = f"Bearer {target.api_key}"
        if "openrouter" in base_url.lower():
            headers["HTTP-Referer"] = "http://localhost:8000"
            headers["X-Title"] = "PCI Procurement System"

        timeout = min(target.timeout_seconds, 15)  # Cap ping test at 15s

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                # First attempt: Try GET /models
                models_endpoint = f"{base_url}/models"
                try:
                    resp = await client.get(models_endpoint, headers=headers)
                    if resp.status_code == 200:
                        latency = int((time.monotonic() - start_time) * 1000)
                        return {
                            "status": "ONLINE",
                            "latency_ms": latency,
                            "runtime_mode": runtime_mode,
                            "provider": provider,
                            "model": model,
                            "endpoint": base_url,
                            "message": f"Koneksi ke endpoint {provider.upper()} berhasil via /models (Latensi: {latency}ms).",
                            "is_fallback": False
                        }
                except Exception:
                    pass

                # Second attempt: Try chat completions with minimal prompt
                chat_endpoint = f"{base_url}/chat/completions"
                body = {
                    "model": model,
                    "messages": [
                        {"role": "user", "content": "ping"}
                    ],
                    "max_tokens": 5,
                    "temperature": 0.0
                }
                resp = await client.post(chat_endpoint, headers=headers, json=body)
                latency = int((time.monotonic() - start_time) * 1000)

                if resp.status_code == 200:
                    return {
                        "status": "ONLINE",
                        "latency_ms": latency,
                        "runtime_mode": runtime_mode,
                        "provider": provider,
                        "model": model,
                        "endpoint": base_url,
                        "message": f"Koneksi ke runtime {provider.upper()} ({model}) berhasil dan responsif (Latensi: {latency}ms).",
                        "is_fallback": False
                    }
                elif resp.status_code == 401:
                    return {
                        "status": "ERROR",
                        "latency_ms": latency,
                        "runtime_mode": runtime_mode,
                        "provider": provider,
                        "model": model,
                        "endpoint": base_url,
                        "message": f"Autentikasi gagal (HTTP 401 Unauthorized): Periksa kembali API Key untuk {provider.upper()}.",
                        "is_fallback": False
                    }
                elif resp.status_code == 429:
                    return {
                        "status": "DEGRADED",
                        "latency_ms": latency,
                        "runtime_mode": runtime_mode,
                        "provider": provider,
                        "model": model,
                        "endpoint": base_url,
                        "message": f"Terhubung namun mencapai batas kuota request (HTTP 429 Rate Limit Exceeded).",
                        "is_fallback": False
                    }
                else:
                    err_text = resp.text[:150]
                    return {
                        "status": "ERROR",
                        "latency_ms": latency,
                        "runtime_mode": runtime_mode,
                        "provider": provider,
                        "model": model,
                        "endpoint": base_url,
                        "message": f"Endpoint mengembalikan status HTTP {resp.status_code}: {err_text}",
                        "is_fallback": False
                    }

        except httpx.TimeoutException:
            latency = int((time.monotonic() - start_time) * 1000)
            msg = f"Koneksi mengalami batas waktu (timeout > {timeout}s) ke {base_url}."
            if runtime_mode == "local":
                msg += " Pastikan service Ollama/Local LLM sedang berjalan (ollama serve)."
            return {
                "status": "OFFLINE",
                "latency_ms": latency,
                "runtime_mode": runtime_mode,
                "provider": provider,
                "model": model,
                "endpoint": base_url,
                "message": msg,
                "is_fallback": target.auto_fallback_to_local
            }
        except httpx.ConnectError as e:
            latency = int((time.monotonic() - start_time) * 1000)
            msg = f"Tidak dapat terhubung ke {base_url}."
            if runtime_mode == "local":
                msg += " Jika menggunakan Docker, gunakan 'http://host.docker.internal:11434/v1' untuk mengakses Ollama di mesin host."
            return {
                "status": "OFFLINE",
                "latency_ms": latency,
                "runtime_mode": runtime_mode,
                "provider": provider,
                "model": model,
                "endpoint": base_url,
                "message": msg,
                "is_fallback": target.auto_fallback_to_local
            }
        except Exception as e:
            latency = int((time.monotonic() - start_time) * 1000)
            return {
                "status": "ERROR",
                "latency_ms": latency,
                "runtime_mode": runtime_mode,
                "provider": provider,
                "model": model,
                "endpoint": base_url,
                "message": f"Gagal menguji koneksi: {str(e)}",
                "is_fallback": target.auto_fallback_to_local
            }


runtime_manager = AIRuntimeManager.get_instance()

