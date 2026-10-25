import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
ROOT = Path(__file__).resolve().parents[1]

def env_path(key, default):
    p = Path(os.getenv(key, default))
    return p if p.is_absolute() else ROOT / p

class Settings:
    env = os.getenv("SSVT_ENV", "development")
    secret_key = os.getenv("SSVT_SECRET_KEY", "unsafe-development-key-change-me")
    invite_code = os.getenv("SSVT_INVITE_CODE", "LOCAL-ONLY-CHANGE-ME")
    admin_token = os.getenv("SSVT_ADMIN_TOKEN", "LOCAL-ONLY-ADMIN-CHANGE-ME")
    database_path = env_path("SSVT_DATABASE_PATH", "data/ssvt.sqlite3")
    upload_dir = env_path("SSVT_UPLOAD_DIR", "data/uploads")
    max_upload_bytes = int(os.getenv("SSVT_MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))
    max_videos_per_user = int(os.getenv("SSVT_MAX_VIDEOS_PER_USER", "2"))
    max_users = int(os.getenv("SSVT_MAX_USERS", "50"))
    llm_enabled = os.getenv("SSVT_LLM_ENABLED", "false").lower() == "true"
    llm_base_url = os.getenv("SSVT_LLM_BASE_URL", "").rstrip("/")
    llm_api_key = os.getenv("SSVT_LLM_API_KEY", "")
    llm_model = os.getenv("SSVT_LLM_MODEL", "")
    llm_max_output_tokens = int(os.getenv("SSVT_LLM_MAX_OUTPUT_TOKENS", "500"))

settings = Settings()
settings.database_path.parent.mkdir(parents=True, exist_ok=True)
settings.upload_dir.mkdir(parents=True, exist_ok=True)
