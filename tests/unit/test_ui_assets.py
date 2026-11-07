"""UI static assets ship with the package."""
from pathlib import Path

FAVICON = Path(__file__).resolve().parents[2] / "src" / "agrogami" / "ui" / "assets" / "favicon.png"


def test_favicon_exists_and_is_png():
    assert FAVICON.is_file()
    assert FAVICON.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
