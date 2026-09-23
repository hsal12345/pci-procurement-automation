from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "PCI Procurement & SPJ System"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Database URLs
    # By default, use PostgreSQL. If SQLite fallback is desired, can be set in .env
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/pci_spjed"
    ASYNC_DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/pci_spjed"
    USE_SQLITE_FALLBACK: bool = False

    # Configurable Storage Paths (from .env)
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    ARTIFACT_STORAGE_PATH: str = "storage/artifacts"
    UPLOAD_STORAGE_PATH: str = "storage/uploads"
    LIBREOFFICE_PATH: str = r"C:\Program Files\LibreOffice\program\soffice.exe"

    # Security
    SECRET_KEY: str = "dev-insecure-secret-key-pci-procurement-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # AI Assistance & Semantic Verification (Phase 4 / Milestone 5)
    AI_ENABLED: bool = True
    AI_PROVIDER: str = "mock"  # "mock", "openrouter", "gemini", "openai", "ollama"
    AI_API_KEY: Optional[str] = None
    AI_BASE_URL: Optional[str] = None
    AI_MODEL: str = "google/gemini-2.0-flash-exp:free"
    AI_MONTHLY_BUDGET_USD: float = 10.0
    AI_REQUEST_TIMEOUT_SECONDS: int = 30
    AI_COST_PER_1K_PROMPT_USD: float = 0.0
    AI_COST_PER_1K_COMPLETION_USD: float = 0.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_artifact_dir(self) -> Path:
        p = Path(self.ARTIFACT_STORAGE_PATH)
        path = p if p.is_absolute() else (self.BASE_DIR / p)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_upload_dir(self) -> Path:
        p = Path(self.UPLOAD_STORAGE_PATH)
        path = p if p.is_absolute() else (self.BASE_DIR / p)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_evidence_dir(self) -> Path:
        path = self.BASE_DIR / "storage" / "evidence"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_libreoffice_path(self) -> str:
        return self.LIBREOFFICE_PATH

    def get_effective_sync_db_url(self) -> str:
        if self.USE_SQLITE_FALLBACK:
            return f"sqlite:///{self.BASE_DIR / 'pci_spjed.db'}"
        return self.DATABASE_URL

    def get_effective_async_db_url(self) -> str:
        if self.USE_SQLITE_FALLBACK:
            return f"sqlite+aiosqlite:///{self.BASE_DIR / 'pci_spjed.db'}"
        return self.ASYNC_DATABASE_URL

    def get_effective_ai_base_url(self) -> str:
        if self.AI_BASE_URL and self.AI_BASE_URL.strip():
            return self.AI_BASE_URL.strip().rstrip("/")
        provider = (self.AI_PROVIDER or "").lower().strip()
        if provider == "openrouter":
            return "https://openrouter.ai/api/v1"
        elif provider == "gemini":
            return "https://generativelanguage.googleapis.com/v1beta/openai"
        elif provider == "ollama":
            return "http://localhost:11434/v1"
        return "https://api.openai.com/v1"


settings = Settings()

# Ensure directories exist
settings.get_upload_dir()
settings.get_artifact_dir()

