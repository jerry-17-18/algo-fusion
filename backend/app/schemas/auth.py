from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuthActorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    role: str
    username: str | None = None
    external_id: str | None = None
    age: int | None = None
    gender: str | None = None


class UserRead(AuthActorRead):
    username: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthActorRead


class PatientLoginRequest(BaseModel):
    patient_id: str
    full_name: str
    age: int


class TokenPayload(BaseModel):
    sub: str
    role: str
