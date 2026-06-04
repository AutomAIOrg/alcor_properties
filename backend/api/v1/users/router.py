import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from api.dependencies import (
    get_create_user_use_case,
    get_current_user,
    get_delete_user_use_case,
    get_get_all_users_use_case,
    get_update_user_use_case,
    require_admin,
)
from api.v1.users.schemas import UserModel, UserResponse
from application.users.create_user_use_case import CreateUserUseCase
from application.users.delete_user_use_case import DeleteUserUseCase
from application.users.get_all_users_user_case import GetAllUsersUseCase
from application.users.update_user_use_case import UpdateUserUseCase
from config import settings
from domain.auth.user_entity import User

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_admin)])

logger = logging.getLogger(__name__)


@router.post("/")
async def create_user(
    user: UserModel,
    create_user_use_case: Annotated[CreateUserUseCase, Depends(get_create_user_use_case)],
):
    logger.info(f"Creando usuario: {user}")
    create_user_use_case.execute(
        User(
            username=user.username,
            password=settings.DEFAULT_PASSWORD,
            name=user.name,
            lastname=user.lastname,
            email=user.email,
            role=user.role,
        )
    )
    logger.info("Usuario creado correctamente")
    return {"message": "Usuario creado correctamente"}


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    delete_user_use_case: Annotated[DeleteUserUseCase, Depends(get_delete_user_use_case)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    logger.info(f"Eliminando usuario: {user_id}")
    delete_user_use_case.execute(user_id, current_user)

    logger.info("Usuario eliminado correctamente")
    return {"message": "Usuario eliminado correctamente"}


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    user: UserModel,
    update_user_use_case: Annotated[UpdateUserUseCase, Depends(get_update_user_use_case)],
):
    logger.info(f"Actualizando usuario: {user}")
    update_user_use_case.execute(
        User(
            id=user_id,
            username=user.username,
            name=user.name,
            lastname=user.lastname,
            email=user.email,
            role=user.role,
        )
    )
    logger.info("Usuario actualizado correctamente")
    return {"message": "Usuario actualizado correctamente"}


@router.get("/")
async def get_users(
    get_all_users_use_case: Annotated[GetAllUsersUseCase, Depends(get_get_all_users_use_case)],
):
    users = get_all_users_use_case.execute()
    return [
        UserResponse(
            id=user.id,
            name=user.name,
            lastname=user.lastname,
            username=user.username,
            email=user.email,
            role=user.role,
        )
        for user in users
    ]
