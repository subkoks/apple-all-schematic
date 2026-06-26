"""Non-interactive Telegram login.

Replaces Telethon's stdin-based ``start()`` with explicit calls whose phone / code /
2FA inputs are supplied by the Qt UI via an :class:`AuthPrompts` provider. The session
persists to the same path the CLI uses (``data/tg_scraper_session``), so a login here is
reused by the CLI and vice-versa.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from telethon import TelegramClient
from telethon.errors import (
    ApiIdInvalidError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
)

from .config import SESSION_FILE


class AuthError(Exception):
    """Raised when authentication cannot complete (bad creds, invalid code, etc.)."""


@runtime_checkable
class AuthPrompts(Protocol):
    """UI-supplied async input provider. Each method resolves when the user submits."""

    async def request_phone(self) -> str: ...
    async def request_code(self) -> str: ...
    async def request_password(self) -> str: ...


async def build_client(api_id: str, api_hash: str) -> TelegramClient:
    """Construct and connect (but not necessarily authorize) a client."""
    try:
        client = TelegramClient(str(SESSION_FILE), int(api_id), api_hash)
    except ValueError as e:
        raise AuthError(f"Invalid API ID: {e}") from e
    await client.connect()
    return client


async def is_authorized(client: TelegramClient) -> bool:
    return await client.is_user_authorized()


async def ensure_authorized(client: TelegramClient, prompts: AuthPrompts) -> None:
    """Walk the login flow if the session is not already authorized.

    Raises :class:`AuthError` with a user-facing message on any failure.
    """
    if await client.is_user_authorized():
        return

    phone = (await prompts.request_phone()).strip()
    try:
        sent = await client.send_code_request(phone)
    except (PhoneNumberInvalidError, ApiIdInvalidError) as e:
        raise AuthError(f"Could not start login: {e.__class__.__name__}") from e

    code = (await prompts.request_code()).strip()
    try:
        await client.sign_in(phone, code, phone_code_hash=sent.phone_code_hash)
    except PhoneCodeInvalidError as e:
        raise AuthError("The login code was invalid.") from e
    except SessionPasswordNeededError:
        password = await prompts.request_password()
        try:
            await client.sign_in(password=password)
        except Exception as e:  # noqa: BLE001 — surface any 2FA failure to the user
            raise AuthError("Two-step password was incorrect.") from e
