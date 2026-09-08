"""Validación de la configuración de recordatorios (RN-26).

Sin base de datos: `_validate_days` es una función pura y las reglas que
comprueba son las del contrato, no las de una consulta.
"""

import pytest

from app.core.exceptions import ValidationError
from app.modules.notifications.service import NotificationsService


def test_ordena_de_mayor_a_menor():
    """El orden en que se dispararán, para que el listado no engañe."""
    assert NotificationsService._validate_days([0, 3, 1]) == [3, 1, 0]


def test_lista_vacia_es_valida():
    assert NotificationsService._validate_days([]) == []


def test_maximo_cinco_valores():
    NotificationsService._validate_days([10, 7, 5, 3, 1])
    with pytest.raises(ValidationError):
        NotificationsService._validate_days([10, 7, 5, 3, 1, 0])


def test_sin_repetidos():
    with pytest.raises(ValidationError):
        NotificationsService._validate_days([3, 3])


def test_los_limites_son_inclusivos():
    assert NotificationsService._validate_days([0, 30]) == [30, 0]


@pytest.mark.parametrize("dia", [-1, 31])
def test_fuera_de_rango(dia: int):
    with pytest.raises(ValidationError):
        NotificationsService._validate_days([dia])
