"""Unit tests for the email client's retry and never-raise behavior."""

import pytest

from app.integrations.email.client import EmailClient, render_email


@pytest.mark.asyncio
async def test_send_without_api_key_logs_and_succeeds():
    # The test settings have RESEND_API_KEY empty: the email is logged, not sent.
    client = EmailClient()
    client._api_key = ""
    result = await client.send(to="ana@ejemplo.com", subject="Hola", html="<p>Hola</p>")
    assert result.success is True
    assert result.provider_message_id == "logged"


@pytest.mark.asyncio
async def test_send_retries_three_times_then_reports_failure(monkeypatch):
    client = EmailClient()
    client._api_key = "re_test_key"
    client._backoff_base = 0  # no real waiting
    attempts = {"count": 0}

    async def _always_fail(**kwargs):
        attempts["count"] += 1
        raise RuntimeError("proveedor caído")

    monkeypatch.setattr(client, "_deliver", _always_fail)
    result = await client.send(to="ana@ejemplo.com", subject="Hola", html="<p>Hola</p>")

    assert attempts["count"] == 3
    assert result.success is False
    assert result.attempts == 3
    assert "proveedor caído" in result.error


@pytest.mark.asyncio
async def test_send_succeeds_on_second_attempt(monkeypatch):
    client = EmailClient()
    client._api_key = "re_test_key"
    client._backoff_base = 0
    attempts = {"count": 0}

    async def _fail_once(**kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("timeout")
        return "msg_123"

    monkeypatch.setattr(client, "_deliver", _fail_once)
    result = await client.send(to="ana@ejemplo.com", subject="Hola", html="<p>Hola</p>")

    assert result.success is True
    assert result.provider_message_id == "msg_123"
    assert result.attempts == 2


def test_render_email_fills_the_template():
    html = render_email(
        "invitation.html",
        role_label="Miembro",
        invite_url="https://app.example/inv/abc",
        expires_at="2026-09-13",
    )
    assert "https://app.example/inv/abc" in html
    assert "Miembro" in html
