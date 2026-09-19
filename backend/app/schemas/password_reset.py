from pydantic import BaseModel, EmailStr, field_validator

from app.schemas.user import validate_password


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetRequestResponse(BaseModel):
    detail: str


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_policy(cls, value: str) -> str:
        return validate_password(value)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_policy(cls, value: str) -> str:
        return validate_password(value)
