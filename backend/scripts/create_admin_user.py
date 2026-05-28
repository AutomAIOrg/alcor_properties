"""Creación de usuario administrador desde variables de entorno."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from passlib.context import CryptContext
from sqlalchemy import select

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from domain.auth.user_entity import Role  # noqa: E402
from infrastructure.database.session import SessionLocal  # noqa: E402
from infrastructure.models.user import UserORM  # noqa: E402

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _required_env(name: str, *, strip: bool = True) -> str:
    value = os.getenv(name)
    if value is None:
        raise RuntimeError(f"Falta la variable de entorno {name}.")

    value = value.strip() if strip else value
    if not value:
        raise RuntimeError(f"La variable de entorno {name} no puede estar vacía.")

    return value


def main() -> int:
    username = _required_env("ADMIN_USERNAME")
    password = _required_env("ADMIN_PASSWORD", strip=False)
    name = _required_env("ADMIN_NAME")
    lastname = _required_env("ADMIN_LASTNAME")
    email = _required_env("ADMIN_EMAIL")
    role = Role.ADMIN

    with SessionLocal() as session:
        existing_user = session.scalar(select(UserORM).where(UserORM.username == username))
        if existing_user is not None:
            print(f"El usuario '{username}' ya existe. No se han hecho cambios.")
            return 0

        existing_email = session.scalar(select(UserORM).where(UserORM.email == email))
        if existing_email is not None:
            raise RuntimeError(f"Ya existe un usuario con el email '{email}'.")

        session.add(
            UserORM(
                username=username,
                password=pwd_context.hash(password),
                name=name,
                lastname=lastname,
                email=email,
                role=role.value,
            )
        )
        session.commit()

    print(f"Usuario administrador '{username}' creado correctamente.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
