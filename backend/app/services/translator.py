from __future__ import annotations

import importlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.config import Settings


# ---------------------------------------------------------------------------
# 数据类：翻译请求
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TranslationRequest:
    """单条翻译请求，包含片段序号与待翻译文本。"""

    index_no: int   # 对应转录片段序号
    text: str       # 待翻译的原文


# ---------------------------------------------------------------------------
# 数据类：翻译结果
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TranslationResult:
    """单条翻译结果，包含序号、译文及成功状态。"""

    index_no: int           # 对应转录片段序号
    translated_text: str    # 翻译结果，失败时为空字符串
    success: bool           # 是否翻译成功
    error: str | None       # 失败时的错误信息


# ---------------------------------------------------------------------------
# 抽象基类
# ---------------------------------------------------------------------------

class Translator(ABC):
    """翻译器抽象基类，所有翻译后端均须实现此接口。"""

    @abstractmethod
    def translate_segments(
        self,
        source_lang: str,
        target_lang: str,
        segments: list[TranslationRequest],
    ) -> list[TranslationResult]:
        """批量翻译片段列表。

        Args:
            source_lang: 源语言代码，支持 "auto" 自动检测。
            target_lang: 目标语言代码，例如 "zh-CN"、"en"。
            segments: 待翻译的 TranslationRequest 列表。

        Returns:
            TranslationResult 列表，长度与输入 segments 完全相同，
            且每个元素与对应输入元素一一对应。
        """


# ---------------------------------------------------------------------------
# DeepTranslator 实现
# ---------------------------------------------------------------------------

class DeepTranslatorTranslator(Translator):
    """基于 deep-translator 库的翻译器实现。

    首版仅实现 Google Translate 服务，预留 service 参数以便后续扩展。
    """

    def __init__(self, service: str = "google") -> None:
        """初始化翻译器。

        Args:
            service: 翻译服务名称，当前仅支持 "google"。

        Raises:
            ImportError: 若 deep-translator 未安装。
        """
        # 检查可选依赖是否可用
        self._check_dependency()
        self._service = service

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _check_dependency() -> None:
        """检查 deep-translator 是否已安装，未安装则抛出 ImportError。"""
        try:
            importlib.import_module("deep_translator")
        except ModuleNotFoundError as exc:
            raise ImportError(
                "deep-translator 未安装。请运行：pip install deep-translator>=1.11.4"
            ) from exc

    def _translate_one(
        self,
        source_lang: str,
        target_lang: str,
        request: TranslationRequest,
    ) -> TranslationResult:
        """翻译单条请求，捕获异常并封装为 TranslationResult。

        Args:
            source_lang: 源语言代码。
            target_lang: 目标语言代码。
            request: 单条翻译请求。

        Returns:
            对应的 TranslationResult。
        """
        # 安全处理空文本：直接返回空字符串成功结果，跳过 API 调用
        if not request.text.strip():
            return TranslationResult(
                index_no=request.index_no,
                translated_text="",
                success=True,
                error=None,
            )

        try:
            from deep_translator import GoogleTranslator  # type: ignore[import-untyped]

            translated = GoogleTranslator(
                source=source_lang,
                target=target_lang,
            ).translate(request.text)

            # None 守卦：翻译器返回空结果时视为失败
            if translated is None:
                return TranslationResult(
                    index_no=request.index_no,
                    translated_text="",
                    success=False,
                    error="翻译器返回空结果",
                )

            return TranslationResult(
                index_no=request.index_no,
                translated_text=translated,
                success=True,
                error=None,
            )
        except Exception as exc:  # noqa: BLE001
            return TranslationResult(
                index_no=request.index_no,
                translated_text="",
                success=False,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def translate_segments(
        self,
        source_lang: str,
        target_lang: str,
        segments: list[TranslationRequest],
    ) -> list[TranslationResult]:
        """逐条翻译片段列表。

        Args:
            source_lang: 源语言代码，支持 "auto" 自动检测。
            target_lang: 目标语言代码，例如 "zh-CN"、"en"。
            segments: 待翻译的 TranslationRequest 列表。

        Returns:
            TranslationResult 列表，长度与输入 segments 完全相同。
        """
        results: list[TranslationResult] = []
        for segment in segments:
            result = self._translate_one(source_lang, target_lang, segment)
            results.append(result)
        return results


# ---------------------------------------------------------------------------
# 工厂函数
# ---------------------------------------------------------------------------

def create_translator_from_settings(settings: Settings) -> Translator:
    """从 Settings 对象创建翻译器实例。

    Args:
        settings: 配置对象（首版未使用其字段，保留参数以备后续扩展）。

    Returns:
        配置好的 DeepTranslatorTranslator 实例（固定使用 Google 服务）。
    """
    return DeepTranslatorTranslator()
