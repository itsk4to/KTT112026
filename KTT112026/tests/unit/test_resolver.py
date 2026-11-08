import pytest

from ktt112026.features.voice.music.resolver import validate_query


def test_resolver_accepts_search_and_http_urls():
    assert validate_query("  nhạc thư giãn ") == "nhạc thư giãn"
    assert validate_query("https://www.youtube.com/watch?v=abc") == "https://www.youtube.com/watch?v=abc"


def test_resolver_rejects_empty_long_and_unsupported_scheme():
    with pytest.raises(ValueError):
        validate_query(" ")
    with pytest.raises(ValueError):
        validate_query("x" * 501)
    with pytest.raises(ValueError, match="HTTP"):
        validate_query("file:///etc/passwd")
