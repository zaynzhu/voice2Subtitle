from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


# ---------------------------------------------------------------------------
# 数据类：单条转录片段
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TranscriptSegment:
    """一条转录片段，包含时间戳、文本与置信度。"""

    index_no: int        # 从 1 开始的序号
    start_ms: int        # 片段开始时间（毫秒）
    end_ms: int          # 片段结束时间（毫秒）
    text: str            # 转录文本
    confidence: float | None  # 置信度 0-1，无法获取时为 None


# ---------------------------------------------------------------------------
# 抽象基类
# ---------------------------------------------------------------------------

class Transcriber(ABC):
    """转录器抽象基类，所有转录后端均须实现此接口。"""

    @abstractmethod
    def transcribe(self, audio_path: str | Path) -> list[TranscriptSegment]:
        """对给定音频文件执行语音转录。

        Args:
            audio_path: 待转录的音频文件路径。

        Returns:
            按顺序排列的 TranscriptSegment 列表。
        """


# ---------------------------------------------------------------------------
# FasterWhisper 实现
# ---------------------------------------------------------------------------

class FasterWhisperTranscriber(Transcriber):
    """基于 faster-whisper 的转录器实现，支持懒加载模型。"""

    def __init__(
        self,
        model_name: str = "base",
        device: str = "auto",
        compute_type: str = "auto",
    ) -> None:
        """初始化转录器（不立即加载模型）。

        Args:
            model_name: Whisper 模型名称，例如 "tiny"、"base"、"small" 等。
            device: 推理设备，"auto" 时自动检测 CUDA 可用性。
            compute_type: 量化精度，"auto" 时根据设备自动选择。
        """
        # 检查可选依赖是否可用（仅检查，不实际导入）
        self._check_dependency()

        # 解析 device
        if device == "auto":
            device = self._detect_device()
        self._device = device

        # 解析 compute_type
        if compute_type == "auto":
            compute_type = "float16" if self._device == "cuda" else "int8"
        self._compute_type = compute_type

        self._model_name = model_name
        self._model = None  # 懒加载，首次 transcribe 时才初始化

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _check_dependency() -> None:
        """检查 faster-whisper 是否已安装，未安装则抛出 ImportError。"""
        try:
            import importlib
            importlib.import_module("faster_whisper")
        except ModuleNotFoundError as exc:
            raise ImportError(
                "faster-whisper 未安装。请运行：pip install faster-whisper>=1.0.0"
            ) from exc

    @staticmethod
    def _detect_device() -> str:
        """检测当前环境是否支持 CUDA，返回对应的设备字符串。"""
        try:
            import torch  # type: ignore[import-untyped]
            if torch.cuda.is_available():
                return "cuda"
        except ModuleNotFoundError:
            pass
        return "cpu"

    def _load_model(self) -> None:
        """懒加载 WhisperModel，仅在首次调用 transcribe 时执行。"""
        from faster_whisper import WhisperModel  # type: ignore[import-untyped]

        self._model = WhisperModel(
            self._model_name,
            device=self._device,
            compute_type=self._compute_type,
        )

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def transcribe(self, audio_path: str | Path) -> list[TranscriptSegment]:
        """对音频文件执行转录并返回片段列表。

        Args:
            audio_path: 待转录的音频文件路径。

        Returns:
            按时间顺序排列的 TranscriptSegment 列表。

        Raises:
            ImportError: 若 faster-whisper 未安装。
        """
        # 首次调用时加载模型
        if self._model is None:
            self._load_model()

        audio_file = str(Path(audio_path))
        segments_iter, _info = self._model.transcribe(audio_file)

        result: list[TranscriptSegment] = []
        for idx, seg in enumerate(segments_iter, start=1):
            # 秒转毫秒
            start_ms = int(round(seg.start * 1000))
            end_ms = int(round(seg.end * 1000))

            # avg_logprob 是对数概率（通常为负数），转换为 0-1 概率
            avg_logprob: float | None = getattr(seg, "avg_logprob", None)
            if avg_logprob is not None:
                confidence: float | None = min(1.0, max(0.0, math.exp(avg_logprob)))
            else:
                confidence = None

            result.append(
                TranscriptSegment(
                    index_no=idx,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    text=seg.text.strip(),
                    confidence=confidence,
                )
            )

        return result


# ---------------------------------------------------------------------------
# 工厂函数
# ---------------------------------------------------------------------------

def create_transcriber_from_settings(settings) -> Transcriber:
    """从 Settings 对象创建转录器实例。

    Args:
        settings: 包含 whisper_model、whisper_device、whisper_compute_type
                  字段的配置对象（通常为 app.config.Settings 实例）。

    Returns:
        配置好的 FasterWhisperTranscriber 实例。
    """
    return FasterWhisperTranscriber(
        model_name=settings.whisper_model,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )
