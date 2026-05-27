"""Voice2Subtitle 后端启动脚本 — 自动选择最佳 Python 环境"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = str(Path(__file__).parent / "backend")
UVICORN_ARGS = ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "19001", "--reload"]


def has_module(python_exe: str, module: str) -> bool:
    try:
        r = subprocess.run(
            [python_exe, "-c", f"import {module}"],
            capture_output=True, timeout=15,
        )
        return r.returncode == 0
    except Exception:
        return False


def find_python_candidates() -> list[str]:
    """Collect Python executables from PATH, cona info, and common locations."""
    candidates = [sys.executable]
    seen = {sys.executable.lower()}

    # 1. Search PATH for python/python3 executables
    for name in ["python", "python3", "python.exe"]:
        found = shutil.which(name)
        if found and found.lower() not in seen:
            candidates.append(found)
            seen.add(found.lower())

    # 2. Try `conda info --base` to find conda root
    conda_exe = shutil.which("conda")
    if conda_exe:
        try:
            r = subprocess.run(
                [conda_exe, "info", "--base"],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0:
                conda_root = r.stdout.strip()
                for python_name in ["python.exe", "python"]:
                    p = str(Path(conda_root) / python_name)
                    if p.lower() not in seen and Path(p).exists():
                        candidates.append(p)
                        seen.add(p.lower())
        except Exception:
            pass

    # 3. Common install locations (Windows/Linux/macOS)
    home = Path.home()
    common = [
        home / "anaconda3" / "python.exe",
        home / "miniconda3" / "python.exe",
        Path("/usr/bin/python3"),
        Path("/usr/local/bin/python3"),
    ]
    for p in common:
        if p.exists() and str(p).lower() not in seen:
            candidates.append(str(p))
            seen.add(str(p).lower())

    return candidates


def find_best_python() -> str:
    """Find the Python with the most ML engines available."""
    candidates = find_python_candidates()

    best_python = sys.executable
    best_score = 0
    best_tags: list[str] = []

    for exe in candidates:
        score = 0
        tags = []
        if has_module(exe, "faster_whisper"):
            score += 1
            tags.append("faster-whisper")
        if has_module(exe, "whisper"):
            score += 1
            tags.append("openai-whisper")
        if has_module(exe, "torch"):
            score += 1
            tags.append("torch")
        if score > best_score:
            best_score = score
            best_python = exe
            best_tags = tags

    if best_python != sys.executable:
        print(f"[Voice2Subtitle] 自动切换 Python: {best_python} (引擎: {', '.join(best_tags)})")
    else:
        if best_score > 0:
            print(f"[Voice2Subtitle] 使用当前 Python: {sys.executable} (引擎: {', '.join(best_tags)})")
        else:
            print(f"[Voice2Subtitle] 警告: 未找到任何 Whisper 引擎，请安装: pip install faster-whisper")

    return best_python


if __name__ == "__main__":
    python_exe = find_best_python()
    cmd = [python_exe] + UVICORN_ARGS
    print(f"[Voice2Subtitle] 启动后端...")
    subprocess.run(cmd, cwd=BACKEND_DIR)