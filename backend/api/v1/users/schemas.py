from pydantic import BaseModel, Field

from domain.auth.user_entity import Role


class UserModel(BaseModel):
    id: int | None = Field(default=None, ge=1)
    username: str
    name: str
    lastname: str
    email: str | None = Field(default=None)
    role: Role


class UserResponse(BaseModel):
    id: int
    name: str
    lastname: str
    email: str | None = None
    username: str
    role: Role
