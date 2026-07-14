import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from api.dependencies import (
    get_create_user_use_case,
    get_current_user,
    get_delete_user_use_case,
    get_get_all_users_use_case,
    get_reset_user_password_use_case,
    get_update_user_use_case,
    require_admin,
)
from api.v1.users.schemas import CreateUserRequest, UpdateUserRequest, UserResponse
from application.users.create_user_use_case import CreateUserData, CreateUserUseCase
from application.users.delete_user_use_case import DeleteUserUseCase
from application.users.get_all_users_use_case import GetAllUsersUseCase
from application.users.reset_user_password_use_case import (
    ResetUserPasswordCommand,
    ResetUserPasswordUseCase,
)
from application.users.update_user_use_case import UpdateUserData, UpdateUserUseCase
from config import settings
from domain.auth.user_entity import User

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_admin)])

logger = logging.getLogger(__name__)


@router.post("/")
async def create_user(
    user: CreateUserRequest,
    create_user_use_case: Annotated[CreateUserUseCase, Depends(get_create_user_use_case)],
):
    logger.info(f"Creando usuario: {user.username} con rol: {user.role}")
    create_user_use_case.execute(
        CreateUserData(
            username=user.username,
            name=user.name,
            role=user.role,
            initial_password=settings.DEFAULT_PASSWORD,
            lastname=user.lastname,
            email=user.email,
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
    user: UpdateUserRequest,
    update_user_use_case: Annotated[UpdateUserUseCase, Depends(get_update_user_use_case)],
):
    logger.info(f"Actualizando usuario: {user.username} con rol: {user.role}")
    update_user_use_case.execute(
        UpdateUserData(
            user_id=user_id,
            username=user.username,
            name=user.name,
            role=user.role,
            lastname=user.lastname,
            email=user.email,
        )
    )
    logger.info("Usuario actualizado correctamente")
    return {"message": "Usuario actualizado correctamente"}


@router.post("/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    reset_user_password_use_case: Annotated[
        ResetUserPasswordUseCase, Depends(get_reset_user_password_use_case)
    ],
):
    """Restablece la contraseña de un usuario a la contraseña inicial del sistema."""
    logger.info(f"Restableciendo la contraseña del usuario {user_id} a la inicial")
    reset_user_password_use_case.execute(
        ResetUserPasswordCommand(
            user_id=user_id,
            initial_password=settings.DEFAULT_PASSWORD,
        )
    )
    logger.info("Contraseña restablecida correctamente")
    return {"message": "Contraseña restablecida a la contraseña inicial."}


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
