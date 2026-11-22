import pytest

from app.core.covers import cover_id_from_url, detect_image_type, is_valid_cover_id, new_cover_id

COVER_ID = "0123456789abcdef0123456789abcdef"


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (b"\xff\xd8\xff\xe0\x00\x10JFIF", "image/jpeg"),
        (b"\x89PNG\r\n\x1a\n\x00\x00", "image/png"),
        (b"RIFF\x24\x00\x00\x00WEBPVP8 ", "image/webp"),
        (b"GIF89a\x01\x00", None),
        (b"<svg xmlns='http://www.w3.org/2000/svg'>", None),
        (b"RIFF\x24\x00\x00\x00WAVE", None),
        (b"", None),
    ],
)
def test_detect_image_type_uses_file_signature(data, expected):
    assert detect_image_type(data) == expected


def test_new_cover_id_is_random_and_valid():
    first, second = new_cover_id(), new_cover_id()
    assert first != second
    assert is_valid_cover_id(first) and is_valid_cover_id(second)


@pytest.mark.parametrize("value", ["", "ABCDEF0123456789abcdef0123456789", "abc", COVER_ID + "0", "../etc/passwd"])
def test_invalid_cover_ids(value):
    assert not is_valid_cover_id(value)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (f"https://biblioteca-personal-api.onrender.com/api/v1/covers/{COVER_ID}", COVER_ID),
        (f"http://localhost:8000/api/v1/covers/{COVER_ID}/", COVER_ID),
        (f"/api/v1/covers/{COVER_ID}?v=1", COVER_ID),
        ("https://covers.openlibrary.org/b/id/123-M.jpg", None),
        (f"https://example.com/covers/{COVER_ID}/extra.jpg", None),
        (None, None),
        ("", None),
    ],
)
def test_cover_id_from_url_only_matches_uploaded_covers(url, expected):
    assert cover_id_from_url(url) == expected
