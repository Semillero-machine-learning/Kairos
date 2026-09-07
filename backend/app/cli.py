"""Command-line utilities. The first administrator is created here, never
through an exposed endpoint (data-model.md 10).

Usage:
    uv run python -m app.cli create_admin
    uv run python -m app.cli create_admin --email admin@x.com --name "Coord" --password ...
"""

import argparse
import asyncio
import getpass
import sys

from app.core.database import SessionLocal
from app.core.enums import GlobalRole
from app.core.exceptions import DomainError
from app.core.security import hash_password
from app.modules.users.service import PASSWORD_MIN_LENGTH, UsersService


async def _create_admin(full_name: str, email: str, password: str) -> None:
    async with SessionLocal() as db:
        service = UsersService(db)
        service.validate_password_strength(password)
        user = await service.create_user(
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
            global_role=GlobalRole.ADMIN,
        )
        await db.commit()
        print(f"Administrador creado: {user.email} (id {user.id})")


def _prompt(value: str | None, label: str) -> str:
    if value:
        return value
    return input(f"{label}: ").strip()


def create_admin_command(args: argparse.Namespace) -> int:
    full_name = _prompt(args.name, "Nombre completo")
    email = _prompt(args.email, "Correo")
    password = args.password or getpass.getpass("Contraseña (mín. 10 caracteres): ")

    if not full_name or not email or not password:
        print("Nombre, correo y contraseña son obligatorios.", file=sys.stderr)
        return 2
    if len(password) < PASSWORD_MIN_LENGTH:
        print(
            f"La contraseña debe tener al menos {PASSWORD_MIN_LENGTH} caracteres.",
            file=sys.stderr,
        )
        return 2

    try:
        asyncio.run(_create_admin(full_name, email, password))
    except DomainError as exc:
        print(f"Error: {exc.message}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli", description="Utilidades de KAIROS")
    sub = parser.add_subparsers(dest="command", required=True)

    p_admin = sub.add_parser("create_admin", help="Crea el primer administrador")
    p_admin.add_argument("--name", help="Nombre completo")
    p_admin.add_argument("--email", help="Correo")
    p_admin.add_argument("--password", help="Contraseña (mín. 10 caracteres)")
    p_admin.set_defaults(func=create_admin_command)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
