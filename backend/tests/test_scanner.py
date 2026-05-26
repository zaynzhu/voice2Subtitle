from app.services.file_utils import fingerprint_file


def test_fingerprint_file_changes_with_size_and_mtime(tmp_path) -> None:
    path = tmp_path / "sample.mp4"
    path.write_bytes(b"abc")
    first = fingerprint_file(path)

    path.write_bytes(b"abcd")
    second = fingerprint_file(path)

    assert first != second


def test_fingerprint_file_contains_path(tmp_path) -> None:
    path = tmp_path / "clip.mkv"
    path.write_bytes(b"content")
    fingerprint = fingerprint_file(path)
    assert str(path.resolve()) in fingerprint
