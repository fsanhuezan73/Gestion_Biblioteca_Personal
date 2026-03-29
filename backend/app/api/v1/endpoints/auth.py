from fastapi import APIRouter, HTTPException, status

from app.db.session import get_db_connection
from app.core.security import hash_password, verify_password, create_access_token
from app.schemas.user import UserCreate, UserOut
from app.schemas.token import Token, LoginRequest

router = APIRouter(prefix="/auth", tags=["Autenticación"])


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
            "SELECT id, hashed_password FROM users WHERE LOWER(email) = LOWER(:email)",
            {"email": credentials.email},
        )
        row = cursor.fetchone()

    if not row or not verify_password(credentials.password, row[1]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(data={"sub": str(row[0])})
    return Token(access_token=token)
