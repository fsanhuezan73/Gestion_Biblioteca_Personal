import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status

from app.db.session import get_db_connection
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from app.core.config import get_settings
from app.core.mail import mail_configured, send_password_reset_link
from app.core.password_recovery import (
    InvalidResetToken,
    InvalidCurrentPassword,
    UnchangedPassword,
    change_password,
    confirm_password_reset,
    issue_password_reset,
)
from app.schemas.password_reset import (
    PasswordChange,
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetRequestResponse,
)
from app.schemas.user import UserCreate, UserOut
from app.schemas.token import Token, LoginRequest

router = APIRouter(prefix="/auth", tags=["Autenticación"])

PASSWORD_RESET_RESPONSE = "Si el correo está registrado, recibirás un enlace de recuperación."
logger = logging.getLogger(__name__)


def process_password_reset_request(email: str, origin: str) -> None:
    try:
        token = issue_password_reset(email, origin)
        if token is not None:
            send_password_reset_link(email.lower(), token)
    except Exception:
        # No registrar direcciones, secretos ni excepciones de Oracle/SMTP que
        # puedan contener datos sensibles. La respuesta ya fue enviada.
        logger.error("Falló el procesamiento de una solicitud de recuperación")


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo usuario",
)
def register(user_in: UserCreate):
    """HU-07: Crea un nuevo usuario con contraseña hasheada (bcrypt)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Verificar si el correo ya existe
        cursor.execute(
            "SELECT id FROM users WHERE LOWER(email) = LOWER(:email)",
            {"email": user_in.email},
        )
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este correo ya está registrado, por favor inicia sesión",
            )

        # Insertar nuevo usuario
        hashed = hash_password(user_in.password)
        cursor.execute(
            """
            INSERT INTO users (email, hashed_password, created_at)
            VALUES (:email, :hashed_password, SYSTIMESTAMP)
            """,
            {
                "email": user_in.email.lower(),
                "hashed_password": hashed,
            },
        )

        # Obtener el id generado
        cursor.execute(
            "SELECT id FROM users WHERE LOWER(email) = LOWER(:email)",
            {"email": user_in.email},
        )
        row = cursor.fetchone()

    return UserOut(id=row[0], email=user_in.email.lower())


@router.post(
    "/login",
    response_model=Token,
    summary="Iniciar sesión y obtener token JWT",
)
def login(credentials: LoginRequest):
    """HU-08: Valida credenciales y retorna un JWT de acceso."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, hashed_password, auth_version FROM users WHERE LOWER(email) = LOWER(:email)",
            {"email": credentials.email},
        )
        row = cursor.fetchone()

    if not row or not verify_password(credentials.password, row[1]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(data={"sub": str(row[0]), "auth_version": row[2]})
    return Token(access_token=token)


@router.post(
    "/password-reset/request",
    response_model=PasswordResetRequestResponse,
    summary="Solicitar un enlace de recuperación de contraseña",
)
def request_password_reset(
    body: PasswordResetRequest, request: Request, background_tasks: BackgroundTasks
):
    settings = get_settings()
    if not settings.password_reset_enabled or not mail_configured(settings):
        raise HTTPException(status_code=503, detail="Recuperación por correo no disponible")

    origin = request.client.host if request.client else "unknown"
    background_tasks.add_task(process_password_reset_request, str(body.email), origin)
    return PasswordResetRequestResponse(detail=PASSWORD_RESET_RESPONSE)


@router.post(
    "/password-reset/confirm",
    response_model=PasswordResetRequestResponse,
    summary="Restablecer la contraseña con un enlace de un solo uso",
)
def confirm_reset(body: PasswordResetConfirm):
    settings = get_settings()
    if not settings.password_reset_enabled or not mail_configured(settings):
        raise HTTPException(status_code=503, detail="Recuperación por correo no disponible")
    try:
        confirm_password_reset(body.token, body.new_password)
    except InvalidResetToken:
        raise HTTPException(status_code=400, detail="Enlace inválido o expirado")
    except UnchangedPassword:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe ser distinta de la actual")
    return PasswordResetRequestResponse(detail="Contraseña actualizada. Inicia sesión nuevamente.")


@router.post(
    "/password/change",
    response_model=PasswordResetRequestResponse,
    summary="Cambiar la contraseña de la cuenta autenticada",
)
def change_account_password(
    body: PasswordChange, current_user_id: int = Depends(get_current_user)
):
    try:
        change_password(current_user_id, body.current_password, body.new_password)
    except InvalidCurrentPassword:
        raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")
    except UnchangedPassword:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe ser distinta de la actual")
    return PasswordResetRequestResponse(detail="Contraseña actualizada. Inicia sesión nuevamente.")
