from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 19000
    db_path: Path = _PROJECT_ROOT / "data" / "app.sqlite3"
    cache_dir: Path = _PROJECT_ROOT / "data" / "cache"
    model_root: Path = _PROJECT_ROOT / "whisper_model"
    output_mode: str = "beside_video"
    default_source_lang: str = "auto"
    default_target_lang: str = "zh-CN"
    whisper_model: str = "auto"
    whisper_device: str = "auto"
    whisper_compute_type: str = "auto"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="V2S_",
        extra="ignore",
    )

    @model_validator(mode="after")
    def _resolve_paths(self) -> "Settings":
        """将相对路径解析为基于项目根目录的绝对路径。"""
        for field in ("db_path", "cache_dir", "model_root"):
            p = getattr(self, field)
            if not p.is_absolute():
                setattr(self, field, (_PROJECT_ROOT / p).resolve())
        return self


settings = Settings()
