"""Guided Telegram login dialog.

Implements the :class:`gui.core.auth.AuthPrompts` protocol. Each ``request_*`` coroutine
shows the relevant step and awaits an :class:`asyncio.Future` resolved when the user
submits — so the flow integrates with the qasync event loop without blocking it or
falling back to stdin.
"""

from __future__ import annotations

import asyncio

from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class LoginCancelled(Exception):
    """Raised when the user dismisses the login dialog before completing it."""


class _Step(QWidget):
    def __init__(self, title: str, hint: str, *, secret: bool = False) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        head = QLabel(title)
        head.setObjectName("SectionTitle")
        sub = QLabel(hint)
        sub.setObjectName("Muted")
        sub.setWordWrap(True)

        self.input = QLineEdit()
        if secret:
            self.input.setEchoMode(QLineEdit.EchoMode.Password)

        layout.addWidget(head)
        layout.addWidget(sub)
        layout.addWidget(self.input)


class LoginDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Connect to Telegram")
        self.setModal(True)
        self.setMinimumWidth(420)
        self._future: asyncio.Future[str] | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        self._stack = QStackedWidget()
        self._phone = _Step(
            "Phone number",
            "Enter the phone number for your Telegram account, including the country "
            "code (e.g. +12025550123).",
        )
        self._code = _Step(
            "Login code",
            "Telegram sent a login code to your app or SMS. Enter it below.",
        )
        self._password = _Step(
            "Two-step password",
            "Your account has two-step verification. Enter your password.",
            secret=True,
        )
        for step in (self._phone, self._code, self._password):
            self._stack.addWidget(step)
        root.addWidget(self._stack)

        self._error = QLabel("")
        self._error.setStyleSheet("color: #ff8a93;")
        self._error.setWordWrap(True)
        self._error.hide()
        root.addWidget(self._error)

        self._submit = QPushButton("Continue")
        self._submit.setObjectName("Primary")
        self._submit.clicked.connect(self._on_submit)
        root.addWidget(self._submit)

        self._phone.input.returnPressed.connect(self._on_submit)
        self._code.input.returnPressed.connect(self._on_submit)
        self._password.input.returnPressed.connect(self._on_submit)

    # ── AuthPrompts implementation ──────────────────────────────────────────────

    async def request_phone(self) -> str:
        return await self._ask(self._phone)

    async def request_code(self) -> str:
        return await self._ask(self._code)

    async def request_password(self) -> str:
        return await self._ask(self._password)

    # ── internals ───────────────────────────────────────────────────────────────

    async def _ask(self, step: _Step) -> str:
        self._error.hide()
        self._stack.setCurrentWidget(step)
        step.input.setFocus()
        if not self.isVisible():
            self.show()
        self.raise_()
        loop = asyncio.get_running_loop()
        self._future = loop.create_future()
        value = await self._future
        return value

    def show_error(self, message: str) -> None:
        self._error.setText(message)
        self._error.show()

    def _on_submit(self) -> None:
        if self._future is None or self._future.done():
            return
        step = self._stack.currentWidget()
        text = step.input.text().strip()
        if not text:
            return
        step.input.clear()
        self._future.set_result(text)

    def reject(self) -> None:
        self._fail()
        super().reject()

    def _fail(self) -> None:
        if self._future is not None and not self._future.done():
            self._future.set_exception(LoginCancelled("Login was cancelled."))
