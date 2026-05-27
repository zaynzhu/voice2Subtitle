from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 19000
    db_path: Path = Path("./data/app.sqlite3")
    cache_dir: Path = Path("./data/cache")
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


settings = Settings()
