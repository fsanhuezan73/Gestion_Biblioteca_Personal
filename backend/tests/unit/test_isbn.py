import pytest

from app.core.isbn import isbn13_to_10, isbn10_to_13, to_isbn13


@pytest.mark.parametrize("raw,expected", [
    ("978-0-451-52493-5", "9780451524935"),
    ("0-306-40615-2", "9780306406157"),
    ("080442957x", "9780804429573"),
    ("9791032305690", "9791032305690"),
    ("9780451524936", None),
    ("9771234567003", None),
    ("12345", None),
    ("", None),
])
def test_to_isbn13(raw, expected):
    assert to_isbn13(raw) == expected


def test_isbn_10_13_roundtrip():
    assert isbn10_to_13("0306406152") == "9780306406157"
    assert isbn13_to_10("9780306406157") == "0306406152"
    assert isbn13_to_10("9780804429573") == "080442957X"
    assert isbn13_to_10("9791032305690") is None
