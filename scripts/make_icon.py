#!/usr/bin/env python3
"""Render the app icon (a schematic-board mark on an Apple-blue squircle) to a PNG.

    python scripts/make_icon.py <out.png> [size]

No third-party deps beyond PySide6 (already a GUI dep). The shell wrapper
``make_icon.sh`` turns the PNG into a full ``.icns`` via sips/iconutil.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
    QBrush,
    QColor,
    QGuiApplication,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)


def render(size: int) -> QImage:
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    s = size
    margin = s * 0.08
    rect = QRectF(margin, margin, s - 2 * margin, s - 2 * margin)
    radius = s * 0.225  # macOS-squircle-ish

    # Background gradient
    grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
    grad.setColorAt(0.0, QColor("#3b78ff"))
    grad.setColorAt(1.0, QColor("#1b4fd0"))
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    p.fillPath(path, QBrush(grad))

    # Schematic "board" motif in white
    white = QColor(255, 255, 255, 235)
    pen = QPen(white, s * 0.018)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)

    inner = QRectF(s * 0.30, s * 0.30, s * 0.40, s * 0.40)
    chip = QPainterPath()
    chip.addRoundedRect(inner, s * 0.04, s * 0.04)
    p.drawPath(chip)

    # Traces + pads radiating from the chip
    cx, cy = s / 2, s / 2
    reach = s * 0.20
    pad_r = s * 0.022
    p.setBrush(QBrush(white))
    points = [
        (cx, inner.top() - reach, cx, inner.top()),
        (cx, inner.bottom() + reach, cx, inner.bottom()),
        (inner.left() - reach, cy, inner.left(), cy),
        (inner.right() + reach, cy, inner.right(), cy),
    ]
    for ex, ey, sx, sy in points:
        p.drawLine(QPointF(sx, sy), QPointF(ex, ey))
        p.drawEllipse(QPointF(ex, ey), pad_r, pad_r)

    # Diagonal corner traces
    diag = s * 0.14
    for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        sx = inner.left() if dx < 0 else inner.right()
        sy = inner.top() if dy < 0 else inner.bottom()
        ex, ey = sx + dx * diag, sy + dy * diag
        p.drawLine(QPointF(sx, sy), QPointF(ex, ey))
        p.drawEllipse(QPointF(ex, ey), pad_r * 0.8, pad_r * 0.8)

    p.end()
    return img


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: make_icon.py <out.png> [size]", file=sys.stderr)
        raise SystemExit(2)
    out = sys.argv[1]
    size = int(sys.argv[2]) if len(sys.argv) > 2 else 1024
    QGuiApplication([])
    img = render(size)
    if not img.save(out, "PNG"):
        print(f"failed to write {out}", file=sys.stderr)
        raise SystemExit(1)
    print(f"wrote {out} ({size}x{size})")


if __name__ == "__main__":
    main()
