"""Programmatic sidebar icons drawn in the app-icon language.

Each glyph sits inside the same rounded-square "chip" silhouette as the app icon, in
Apple-blue, with rounded strokes and small pad dots echoing the icon's traces. Rendered
at 2x for crisp HiDPI. Accent blue is identical in both themes, so icons match the app
icon and need no per-theme recolor.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

ACCENT = "#2f6df6"
_SCALE = 2


def _pixmap(size: int, draw: Callable[[QPainter, float, QColor], None], color: str) -> QPixmap:
    pm = QPixmap(size * _SCALE, size * _SCALE)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    qcolor = QColor(color)
    pen = QPen(qcolor, 1.7 * _SCALE)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    draw(p, size * _SCALE, qcolor)
    p.end()
    pm.setDevicePixelRatio(_SCALE)
    return pm


def _chip(p: QPainter, s: float) -> QRectF:
    """The shared rounded-square silhouette + two pad dots, like the app icon."""
    m = s * 0.10
    rect = QRectF(m, m, s - 2 * m, s - 2 * m)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(rect, s * 0.24, s * 0.24)
    return rect


def _draw_download(p: QPainter, s: float, c: QColor) -> None:
    r = _chip(p, s)
    cx = r.center().x()
    top = r.top() + r.height() * 0.22
    mid = r.top() + r.height() * 0.52
    # shaft
    p.drawLine(QPointF(cx, top), QPointF(cx, mid))
    # arrow head
    a = r.width() * 0.16
    p.drawLine(QPointF(cx - a, mid - a), QPointF(cx, mid))
    p.drawLine(QPointF(cx + a, mid - a), QPointF(cx, mid))
    # tray
    by = r.bottom() - r.height() * 0.22
    p.drawLine(QPointF(r.left() + r.width() * 0.28, by), QPointF(r.right() - r.width() * 0.28, by))


def _draw_organize(p: QPainter, s: float, c: QColor) -> None:
    r = _chip(p, s)
    p.setBrush(c)
    dot = r.width() * 0.075
    xs = (r.left() + r.width() * 0.36, r.left() + r.width() * 0.64)
    ys = (r.top() + r.height() * 0.36, r.top() + r.height() * 0.64)
    for x in xs:
        for y in ys:
            p.drawEllipse(QPointF(x, y), dot, dot)
    p.setBrush(Qt.BrushStyle.NoBrush)


def _draw_settings(p: QPainter, s: float, c: QColor) -> None:
    r = _chip(p, s)
    knob = r.width() * 0.075
    rows = (0.34, 0.5, 0.66)
    knob_x = (0.62, 0.40, 0.58)
    for row, kx in zip(rows, knob_x, strict=True):
        y = r.top() + r.height() * row
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(
            QPointF(r.left() + r.width() * 0.26, y), QPointF(r.right() - r.width() * 0.26, y)
        )
        p.setBrush(c)
        p.drawEllipse(QPointF(r.left() + r.width() * kx, y), knob, knob)
    p.setBrush(Qt.BrushStyle.NoBrush)


_GLYPHS: dict[str, Callable[[QPainter, float, QColor], None]] = {
    "download": _draw_download,
    "organize": _draw_organize,
    "settings": _draw_settings,
}


def nav_icon(name: str, size: int = 18, color: str = ACCENT) -> QIcon:
    draw = _GLYPHS.get(name)
    if draw is None:
        return QIcon()
    return QIcon(_pixmap(size, draw, color))
