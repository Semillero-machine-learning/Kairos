"""Resend email client with retries and HTML templates.

A mail failure never propagates to the business operation that triggered it
(RN-30, EB-08): send() returns a result and never raises. Up to 3 attempts with
increasing backoff. When RESEND_API_KEY is empty the email is logged instead of
sent, so development and tests need no external service.
"""

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

import httpx
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import get_settings

logger = logging.getLogger("kairos.email")

_RESEND_ENDPOINT = "https://api.resend.com/emails"
_MAX_ATTEMPTS = 3
_TEMPLATES_DIR = Path(__file__).parent / "templates"

_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def render_email(template_name: str, **context: object) -> str:
    return _jinja_env.get_template(template_name).render(**context)


@dataclass
class EmailResult:
    success: bool
    provider_message_id: str | None = None
    error: str | None = None
    attempts: int = 0


class EmailClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.resend_api_key
        self._sender = settings.email_from
        self._backoff_base = 0.5  # seconds; tests may set to 0

    async def send(self, *, to: str, subject: str, html: str) -> EmailResult:
        if not self._api_key:
            logger.info(
                "Correo no enviado (RESEND_API_KEY vacía). to=%s subject=%s", to, subject
            )
            return EmailResult(success=True, provider_message_id="logged", attempts=0)

        last_error: str | None = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                message_id = await self._deliver(to=to, subject=subject, html=html)
                return EmailResult(
                    success=True, provider_message_id=message_id, attempts=attempt
                )
            except Exception as exc:  # noqa: BLE001 - any failure is logged and retried
                last_error = str(exc)
                logger.warning(
                    "Fallo al enviar correo (intento %d/%d) to=%s: %s",
                    attempt,
                    _MAX_ATTEMPTS,
                    to,
                    last_error,
                )
                if attempt < _MAX_ATTEMPTS:
                    await asyncio.sleep(self._backoff_base * attempt)

        return EmailResult(success=False, error=last_error, attempts=_MAX_ATTEMPTS)

    async def _deliver(self, *, to: str, subject: str, html: str) -> str:
        payload = {"from": self._sender, "to": [to], "subject": subject, "html": html}
        headers = {"Authorization": f"Bearer {self._api_key}"}
        async with httpx.AsyncClient(timeout=10.0) as http:
            response = await http.post(_RESEND_ENDPOINT, json=payload, headers=headers)
            response.raise_for_status()
            return response.json().get("id", "")
