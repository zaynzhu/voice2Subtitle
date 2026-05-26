from types import SimpleNamespace

from app.services.subtitle_writer import choose_segment_text, format_timestamp, write_srt


def test_format_timestamp() -> None:
    assert format_timestamp(0) == "00:00:00,000"
    assert format_timestamp(3723401) == "01:02:03,401"


def test_choose_segment_text_prefers_edited_text() -> None:
    segment = SimpleNamespace(
        edited_text=" final ",
        translated_text="translated",
        source_text="source",
    )
    assert choose_segment_text(segment) == "final"


def test_write_srt(tmp_path) -> None:
    segments = [
        SimpleNamespace(start_ms=0, end_ms=1000, edited_text="", translated_text="hello", source_text=""),
        SimpleNamespace(start_ms=1000, end_ms=2000, edited_text="world", translated_text="", source_text=""),
    ]
    output = write_srt(segments, tmp_path / "out.srt")
    content = output.read_text(encoding="utf-8")
    assert "00:00:00,000 --> 00:00:01,000" in content
    assert "hello" in content
    assert "world" in content
