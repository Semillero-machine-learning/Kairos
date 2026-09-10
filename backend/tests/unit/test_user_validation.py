"""Unit tests for the credential checks that guard account creation.

The email one exists because the CLI is the only path that does not go through
a Pydantic schema, and it is the path that creates the first administrator: an
address the API's ``EmailStr`` rejects used to produce an account that could
never sign in, on a deployment with no other way in.
"""

import pytest

from app.core.exceptions import ValidationError
from app.modules.users.service import PASSWORD_MIN_LENGTH, UsersService


@pytest.mark.parametrize(
    "email",
    [
        "coordinadora@semillero.dev",
        "ana.moreno+tareas@universidad.edu.co",
        "b@c.io",
    ],
)
def test_correos_validos_pasan(email):
    UsersService.validate_email(email)


@pytest.mark.parametrize(
    ("email", "por_que"),
    [
        ("coord@kairos.test", "«.test» es un dominio reservado y el validador lo rechaza"),
        ("sin-arroba.dev", "no tiene arroba"),
        ("dos@@arrobas.dev", "arroba repetida"),
        ("@semillero.dev", "no hay parte local"),
        ("coord@", "no hay dominio"),
        ("", "vacío"),
        ("   ", "solo espacios"),
    ],
)
def test_correos_que_el_login_rechazaria_no_crean_cuenta(email, por_que):
    with pytest.raises(ValidationError) as exc:
        UsersService.validate_email(email)
    # El mensaje va en español y dice cuál era el correo, que es lo que
    # necesita quien acaba de teclearlo mal en la terminal.
    assert "no es un correo válido" in exc.value.message, por_que


def test_la_contrasena_corta_se_rechaza():
    with pytest.raises(ValidationError):
        UsersService.validate_password_strength("a" * (PASSWORD_MIN_LENGTH - 1))

    UsersService.validate_password_strength("a" * PASSWORD_MIN_LENGTH)
