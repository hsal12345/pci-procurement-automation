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
    AI_PROVIDER: str = "mock"  # "mock", "openrouter", "gemini", "openai", "deepseek", "ollama"
    AI_API_KEY: Optional[str] = None
    AI_BASE_URL: Optional[str] = None
    AI_MODEL: str = "google/gemini-2.0-flash-exp:free"
    AI_MONTHLY_BUDGET_USD: float = 10.0
    AI_REQUEST_TIMEOUT_SECONDS: int = 30
    AI_COST_PER_1K_PROMPT_USD: float = 0.0
    AI_COST_PER_1K_COMPLETION_USD: float = 0.0

    # Google Drive Storage Integration
    DRIVE_SYNC_ENABLED: bool = True
    DRIVE_SYNC_MODE: str = "auto"  # "auto", "live", "mock"
    GOOGLE_DRIVE_CREDENTIALS_PATH: str = "credentials/gdrive-service-account.json"
    GOOGLE_DRIVE_FOLDER_ID_PATH: str = "credentials/gdrive-folder-id.txt"
    GOOGLE_DRIVE_OAUTH_CLIENT_PATH: str = "credentials/gdrive-oauth-client.json"
    GOOGLE_DRIVE_OAUTH_TOKEN_PATH: str = "credentials/gdrive-oauth-token.json"
    GOOGLE_DRIVE_OAUTH_REDIRECT_URI: str = "http://localhost:8000/api/v1/archive/oauth/callback"
    GOOGLE_DRIVE_ROOT_FOLDER_ID: Optional[str] = None

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
        elif provider == "deepseek":
            return "https://api.deepseek.com/v1"
        elif provider == "ollama":
            return "http://localhost:11434/v1"
        return "https://api.openai.com/v1"

    def get_drive_credentials_path(self) -> Path:
        p = Path(self.GOOGLE_DRIVE_CREDENTIALS_PATH)
        return p if p.is_absolute() else (self.BASE_DIR / p)

    def get_drive_oauth_client_path(self) -> Path:
        p = Path(self.GOOGLE_DRIVE_OAUTH_CLIENT_PATH)
        return p if p.is_absolute() else (self.BASE_DIR / p)

    def get_drive_oauth_token_path(self) -> Path:
        p = Path(self.GOOGLE_DRIVE_OAUTH_TOKEN_PATH)
        return p if p.is_absolute() else (self.BASE_DIR / p)

    def is_drive_oauth_configured(self) -> bool:
        return self.get_drive_oauth_token_path().exists()

    def get_effective_drive_root_folder_id(self) -> Optional[str]:
        if self.GOOGLE_DRIVE_ROOT_FOLDER_ID and self.GOOGLE_DRIVE_ROOT_FOLDER_ID.strip():
            return self.GOOGLE_DRIVE_ROOT_FOLDER_ID.strip()
        p = Path(self.GOOGLE_DRIVE_FOLDER_ID_PATH)
        path = p if p.is_absolute() else (self.BASE_DIR / p)
        if path.exists():
            content = path.read_text(encoding="utf-8").strip()
            if content:
                return content
        return None

    def is_drive_live_configured(self) -> bool:
        if not self.DRIVE_SYNC_ENABLED:
            return False
        if (self.DRIVE_SYNC_MODE or "").lower().strip() == "mock":
            return False
        has_auth = self.is_drive_oauth_configured() or self.get_drive_credentials_path().exists()
        return has_auth and bool(self.get_effective_drive_root_folder_id())


settings = Settings()

# Ensure directories exist
settings.get_upload_dir()
settings.get_artifact_dir()

