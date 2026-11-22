from oracledb import DB_TYPE_BLOB

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from starlette.concurrency import run_in_threadpool

from app.core.covers import MAX_COVER_BYTES, detect_image_type, is_valid_cover_id, new_cover_id
from app.core.security import get_current_user
from app.db.session import get_db_connection
from app.schemas.cover import CoverOut

router = APIRouter(prefix="/covers", tags=["Portadas"])

_TOO_LARGE = "La imagen supera el tamaño máximo de 2 MB"


def _insert_cover(cover_id: str, user_id: int, content_type: str, data: bytes) -> None:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Sin esto, los binds de más de 32 KB fallan como RAW.
        cursor.setinputsizes(data=DB_TYPE_BLOB)
        cursor.execute(
            "INSERT INTO book_covers (id, user_id, content_type, byte_size, data) "
            "VALUES (:id, :user_id, :content_type, :byte_size, :data)",
            {
                "id": cover_id,
                "user_id": user_id,
                "content_type": content_type,
                "byte_size": len(data),
                "data": data,
            },
        )


@router.post(
    "",
    response_model=CoverOut,
    status_code=status.HTTP_201_CREATED,
    summary="Subir una imagen de portada",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {t: {"schema": {"type": "string", "format": "binary"}}
                        for t in ("image/jpeg", "image/png", "image/webp")},
        }
    },
)
async def upload_cover(request: Request, current_user_id: int = Depends(get_current_user)):
    """Recibe la imagen como cuerpo binario (JPEG, PNG o WebP, máximo 2 MB).

    Devuelve el id; la URL pública es `/api/v1/covers/{id}` y se guarda en
    `cover_url` al crear o editar el libro."""
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_COVER_BYTES:
        raise HTTPException(status_code=413, detail=_TOO_LARGE)

    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > MAX_COVER_BYTES:
            raise HTTPException(status_code=413, detail=_TOO_LARGE)
    if not data:
        raise HTTPException(status_code=422, detail="No se recibió ninguna imagen")

    content_type = detect_image_type(bytes(data[:16]))
    if content_type is None:
        raise HTTPException(status_code=415, detail="Formato no soportado. Usa una imagen JPEG, PNG o WebP")

    cover_id = new_cover_id()
    # La escritura en Oracle es bloqueante: fuera del event loop.
    await run_in_threadpool(_insert_cover, cover_id, current_user_id, content_type, bytes(data))
    return CoverOut(id=cover_id, content_type=content_type, byte_size=len(data))


@router.get(
    "/{cover_id}",
    summary="Obtener una imagen de portada",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}, "image/png": {}, "image/webp": {}}}},
)
def get_cover(cover_id: str):
    """Público: una etiqueta <img> no puede enviar el JWT. El id es un UUID
    aleatorio no adivinable y la imagen nunca cambia (reemplazar crea otro id)."""
    if not is_valid_cover_id(cover_id):
        raise HTTPException(status_code=404, detail="Portada no encontrada")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT content_type, data FROM book_covers WHERE id = :id",
            {"id": cover_id},
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Portada no encontrada")
        content_type, data = row
        # Leer el BLOB antes de devolver la conexión al pool.
        if hasattr(data, "read"):
            data = data.read()
    return Response(
        content=data,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "X-Content-Type-Options": "nosniff",
        },
    )
