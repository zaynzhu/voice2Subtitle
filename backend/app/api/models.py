from fastapi import APIRouter
from pathlib import Path

from app.config import settings

router = APIRouter(prefix="/api", tags=["models"])


def _detect_engines() -> dict:
    available = []
    try:
        import faster_whisper  # noqa: F401
        available.append("faster-whisper")
    except ImportError:
        pass
    try:
        import whisper  # noqa: F401
        available.append("openai-whisper")
    except ImportError:
        pass
    return {
        "available": available,
        "faster_whisper": "faster-whisper" in available,
        "openai_whisper": "openai-whisper" in available,
    }


@router.get("/models")
def list_models() -> dict:
    model_root = Path(settings.model_root).resolve()
    models = []

    if model_root.exists():
        # Scan for CTranslate2 model directories (have model.bin or config.json)
        for child in sorted(model_root.iterdir()):
            if not child.is_dir():
                continue
            is_ctranslate2 = (child / "model.bin").exists() or (child / "config.json").exists()
            size_mb = sum(f.stat().st_size for f in child.rglob("*") if f.is_file()) / (1024 * 1024)
            models.append({
                "name": child.name,
                "type": "ctranslate2" if is_ctranslate2 else "unknown",
                "size_mb": round(size_mb, 1),
            })

        # Scan for .pt files at root level (openai-whisper format)
        for pt_file in sorted(model_root.glob("*.pt")):
            size_mb = pt_file.stat().st_size / (1024 * 1024)
            models.append({
                "name": pt_file.stem,
                "type": "openai-whisper",
                "size_mb": round(size_mb, 1),
            })

    # Detect GPU info
    gpu_info = None
    try:
        import torch
        if torch.cuda.is_available():
            gpu_info = {
                "device": torch.cuda.get_device_name(0),
                "vram_mb": round(torch.cuda.get_device_properties(0).total_memory / (1024 * 1024)),
            }
    except ImportError:
        pass

    return {
        "model_root": str(model_root),
        "active_model": settings.whisper_model,
        "models": models,
        "engines": _detect_engines(),
        "gpu": gpu_info,
    }