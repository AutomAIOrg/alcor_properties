from pydantic import BaseModel, Field

from domain.auth.user_entity import Role


class CreateUserRequest(BaseModel):
    username: str
    name: str
    role: Role
    lastname: str | None = None
    email: str | None = Field(default=None)


class UpdateUserRequest(BaseModel):
    username: str
    name: str
    role: Role
    lastname: str | None = None
    email: str | None = Field(default=None)


class UserResponse(BaseModel):
    id: int
    name: str
    lastname: str | None = None
    email: str | None = None
    username: str
    role: Role
