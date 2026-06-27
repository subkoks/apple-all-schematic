"""Theme management: token palettes + system/dark/light application.

Loads the ``theme.qss`` template, substitutes ``@TOKEN@`` placeholders with the active
palette, and applies it to the QApplication. In ``system`` mode it follows the OS via
``QStyleHints.colorScheme()`` (Qt 6.5+) and re-applies live on ``colorSchemeChanged``.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

THEME_FILE = Path(__file__).resolve().parent / "theme.qss"

DARK: dict[str, str] = {
    "BG": "#16181d",
    "SURFACE": "#1b1e24",
    "CARD": "#1d2128",
    "FIELD": "#14161b",
    "LOGBG": "#101216",
    "BORDER": "#262a32",
    "BORDER2": "#2d323c",
    "SURFACE2": "#232730",
    "HOVER": "#2a2f3a",
    "SELECT": "#243043",
    "TEXT": "#e6e8ec",
    "TEXTSTRONG": "#f3f4f6",
    "TEXTDIM": "#aab1bd",
    "MUTED": "#8a92a0",
    "ACCENT": "#2f6df6",
    "ACCENTHOVER": "#3b78ff",
    "ACCENTTEXT": "#ffffff",
    "ACCENTDISABLEDBG": "#2a3650",
    "ACCENTDISABLEDTEXT": "#8d9bb5",
    "DANGERBG": "#3a2126",
    "DANGERBORDER": "#5a2a31",
    "DANGERTEXT": "#ff8a93",
    "SCROLL": "#313742",
    "SCROLLHOVER": "#3c434f",
    "DISABLEDTEXT": "#565d68",
    "DISABLEDBG": "#1c1f25",
}

LIGHT: dict[str, str] = {
    "BG": "#f5f6f8",
    "SURFACE": "#ffffff",
    "CARD": "#ffffff",
    "FIELD": "#ffffff",
    "LOGBG": "#f0f2f5",
    "BORDER": "#e2e5ea",
    "BORDER2": "#d4d9e0",
    "SURFACE2": "#eef1f5",
    "HOVER": "#e6eaf0",
    "SELECT": "#dbe6fb",
    "TEXT": "#1c1f25",
    "TEXTSTRONG": "#0f1115",
    "TEXTDIM": "#4a5160",
    "MUTED": "#6b7280",
    "ACCENT": "#2f6df6",
    "ACCENTHOVER": "#1f5fe6",
    "ACCENTTEXT": "#ffffff",
    "ACCENTDISABLEDBG": "#aac3f7",
    "ACCENTDISABLEDTEXT": "#ffffff",
    "DANGERBG": "#fdecee",
    "DANGERBORDER": "#f4c2c8",
    "DANGERTEXT": "#c0303b",
    "SCROLL": "#c8cdd6",
    "SCROLLHOVER": "#b3bac6",
    "DISABLEDTEXT": "#a0a6b0",
    "DISABLEDBG": "#eef0f3",
}


def render(palette: dict[str, str], template: str | None = None) -> str:
    """Substitute @TOKEN@ placeholders in the QSS template. Trailing '@' avoids
    prefix collisions (e.g. @ACCENT@ vs @ACCENTHOVER@)."""
    qss = template if template is not None else THEME_FILE.read_text()
    for token, value in palette.items():
        qss = qss.replace(f"@{token}@", value)
    return qss


class ThemeManager(QObject):
    """Applies and tracks the active theme for a QApplication."""

    def __init__(self, app: QApplication, mode: str = "system") -> None:
        super().__init__(app)
        self._app = app
        self._mode = mode if mode in ("system", "dark", "light") else "system"
        self._template = THEME_FILE.read_text() if THEME_FILE.exists() else ""
        hints = app.styleHints()
        if hasattr(hints, "colorSchemeChanged"):
            hints.colorSchemeChanged.connect(self._on_system_changed)

    @property
    def mode(self) -> str:
        return self._mode

    def set_mode(self, mode: str) -> None:
        self._mode = mode if mode in ("system", "dark", "light") else "system"
        self.apply()

    def effective_is_dark(self) -> bool:
        if self._mode == "dark":
            return True
        if self._mode == "light":
            return False
        scheme = QGuiApplication.styleHints().colorScheme()
        return scheme == Qt.ColorScheme.Dark

    def apply(self) -> None:
        palette = DARK if self.effective_is_dark() else LIGHT
        self._app.setStyleSheet(render(palette, self._template))

    def _on_system_changed(self, _scheme) -> None:
        if self._mode == "system":
            self.apply()
