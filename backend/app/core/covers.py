"""Reglas puras para las portadas subidas por el usuario (sin base de datos)."""
import re
import uuid

# El frontend comprime a JPEG antes de subir; este límite cubre imágenes sin comprimir.
MAX_COVER_BYTES = 2 * 1024 * 1024

_COVER_ID_RE = re.compile(r"^[0-9a-f]{32}$")
# Una URL de portada propia termina en /covers/<id>, sin importar el host.
_INTERNAL_URL_RE = re.compile(r"/covers/([0-9a-f]{32})/?$")


def detect_image_type(data: bytes) -> str | None:
    """Tipo MIME según la firma del archivo; None si no es JPEG, PNG ni WebP."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def new_cover_id() -> str:
    return uuid.uuid4().hex


def is_valid_cover_id(cover_id: str) -> bool:
    return bool(_COVER_ID_RE.match(cover_id))


def cover_id_from_url(url: str | None) -> str | None:
    """Id de la portada si la URL apunta a una imagen subida a la app."""
    if not url:
        return None
    match = _INTERNAL_URL_RE.search(url.split("?", 1)[0])
    return match.group(1) if match else None
