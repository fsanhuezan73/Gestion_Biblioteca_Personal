from datetime import date

from app.core.recommendations import (
    authors_match, build_profile, in_library, next_daily_count, normalize_text, normalize_title,
    rated_read_books, remaining_today, titles_match,
)

TODAY = date(2026, 11, 23)


def book(title, authors, status="Leído", rating=4, finished_at=None, genre="Novela"):
    return {"title": title, "authors": authors, "reading_status": status, "rating": rating,
            "finished_at": finished_at, "genre": genre}


def test_normalize_removes_accents_punctuation_and_case():
    assert normalize_text("  Cien Años de Soledad! ") == "cien anos de soledad"
    assert normalize_title("El nombre del viento (Crónica del asesino de reyes 1)") == "el nombre del viento"
    assert normalize_title("Sapiens: De animales a dioses") == "sapiens"


def test_titles_match_exact_prefix_and_rejects_short_prefix():
    assert titles_match("Cien años de soledad", "CIEN AÑOS DE SOLEDAD")
    assert titles_match("El principito", "El principito edición ilustrada")
    assert not titles_match("Dune", "Dune Messiah")  # una sola palabra no basta como prefijo
    assert not titles_match("Rayuela", "")


def test_authors_match_by_surname():
    assert authors_match("Gabriel García Márquez", ["Gabriel Garcia Marquez"])
    assert authors_match("J.R.R. Tolkien", ["John Ronald Reuel Tolkien"])
    assert not authors_match("Isabel Allende", ["Gabriel García Márquez"])
    assert not authors_match("", ["Alguien"])


def test_in_library_requires_title_and_author_or_missing_authors():
    library = [book("Rayuela", ["Julio Cortázar"]), book("Sin autor", [])]
    assert in_library("Rayuela", ["Julio Cortazar"], library)
    assert not in_library("Rayuela", ["Otro Autor Distinto"], library)
    assert in_library("Sin autor", ["Cualquiera"], library)
    assert not in_library("Otro libro", ["Julio Cortázar"], library)


def test_profile_only_rated_read_books_sorted_and_without_private_fields():
    library = [
        book("A", ["Autor Uno"], rating=3, finished_at=date(2026, 1, 1)),
        book("B", ["Autor Dos"], rating=5, finished_at=date(2025, 1, 1)),
        book("C", ["Autor Tres"], rating=5, finished_at=date(2026, 6, 1)),
        book("D", ["Autor Cuatro"], status="Quiero leer", rating=5),
        book("E", ["Autor Cinco"], rating=None),
        {**book("F", ["Autor Seis"], rating=4), "personal_notes": "secreto"},
    ]
    profile = build_profile(library)
    assert [p["titulo"] for p in profile] == ["C", "B", "F", "A"]
    assert set(profile[0]) == {"titulo", "autor", "genero", "estrellas"}
    assert "secreto" not in str(profile)
    assert len(rated_read_books(library)) == 4


def test_profile_is_capped_at_40_books():
    library = [book(f"Libro {i}", [f"Autor {i}"]) for i in range(60)]
    assert len(build_profile(library)) == 40


def test_daily_counter_resets_on_new_day():
    assert remaining_today(None, None, TODAY, 5) == 5
    assert remaining_today(3, TODAY, TODAY, 5) == 2
    assert remaining_today(7, TODAY, TODAY, 5) == 0
    assert remaining_today(5, date(2026, 11, 22), TODAY, 5) == 5
    assert next_daily_count(5, date(2026, 11, 22), TODAY) == 1
    assert next_daily_count(2, TODAY, TODAY) == 3
