"""
Avatar Rendering Utilities (PySide6)
Generates high-DPI circular profile avatars with image caching, auto-scaling, and role-colored initials.
"""
from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPixmap, QPainter, QPainterPath, QBrush, QColor, QFont, QPen

def get_role_color(role: str) -> str:
    """Returns primary branding accent color for a given RBAC role."""
    r = (role or "").upper()
    if r == "ADMIN":
        return "#1E40AF"  # Deep Blue
    elif r == "HOD":
        return "#6D28D9"  # Royal Purple
    elif r == "FACULTY":
        return "#047857"  # Emerald Green
    elif r == "LAB_INSTRUCTOR":
        return "#B45309"  # Amber Bronze
    elif r == "HR":
        return "#C026D3"  # Vibrant Fuchsia
    elif r == "PRINCIPAL":
        return "#B91C1C"  # Crimson Red
    return "#475569"      # Slate Gray


def create_circular_avatar(
    image_path: Optional[str] = None,
    size: int = 40,
    name: str = "User",
    role: str = "FACULTY",
) -> QPixmap:
    """
    Renders an antialiased circular avatar QPixmap.
    If image_path points to an existing file, loads, center-crops, and draws the picture.
    Otherwise, renders a styled disc with the user's capitalized initials.
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)

    path = QPainterPath()
    path.addEllipse(0, 0, size, size)
    painter.setClipPath(path)

    loaded = False
    if image_path:
        # Check both absolute path and relative-to-project path
        p = Path(image_path)
        if not p.is_absolute():
            base_dir = Path(__file__).resolve().parent.parent
            p = base_dir / image_path

        if p.exists() and p.is_file():
            src = QPixmap(str(p))
            if not src.isNull():
                scaled = src.scaled(
                    size, size,
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation
                )
                x = (scaled.width() - size) // 2
                y = (scaled.height() - size) // 2
                painter.drawPixmap(0, 0, scaled.copy(x, y, size, size))
                loaded = True

    if not loaded:
        bg_hex = get_role_color(role)
        painter.fillPath(path, QBrush(QColor(bg_hex)))
        painter.setPen(QColor("#FFFFFF"))

        parts = [part for part in name.strip().split() if part]
        if len(parts) >= 2:
            initials = f"{parts[0][0]}{parts[1][0]}".upper()
        elif len(parts) == 1 and len(parts[0]) >= 2:
            initials = parts[0][:2].upper()
        elif len(parts) == 1:
            initials = parts[0][0].upper()
        else:
            initials = "U"

        font_size = max(8, int(size * 0.38))
        font = QFont("Segoe UI", font_size, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRect(0, 0, size, size), Qt.AlignCenter, initials)

    # Clean outer border ring
    painter.setClipping(False)
    painter.setPen(QPen(QColor("#CBD5E1"), max(1, size // 30)))
    painter.drawEllipse(0, 0, size - 1, size - 1)
    painter.end()

    return pixmap


def create_square_avatar(
    image_path: Optional[str] = None,
    size: int = 72,
    radius: int = 8,
    name: str = "User",
    role: str = "FACULTY",
) -> QPixmap:
    """
    Renders an antialiased square avatar QPixmap with rounded corners.
    If image_path points to an existing file, loads, center-crops to square,
    and draws the picture clipped to the rounded rectangle.
    Otherwise, renders a styled rounded square with the user's capitalized initials.
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)

    path = QPainterPath()
    path.addRoundedRect(0, 0, size, size, radius, radius)
    painter.setClipPath(path)

    loaded = False
    if image_path:
        p = Path(image_path)
        if not p.is_absolute():
            base_dir = Path(__file__).resolve().parent.parent
            p = base_dir / image_path

        if p.exists() and p.is_file():
            src = QPixmap(str(p))
            if not src.isNull():
                scaled = src.scaled(
                    size, size,
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation
                )
                x = (scaled.width() - size) // 2
                y = (scaled.height() - size) // 2
                painter.drawPixmap(0, 0, scaled.copy(x, y, size, size))
                loaded = True

    if not loaded:
        bg_hex = get_role_color(role)
        painter.fillPath(path, QBrush(QColor(bg_hex)))
        painter.setPen(QColor("#FFFFFF"))

        parts = [part for part in name.strip().split() if part]
        if len(parts) >= 2:
            initials = f"{parts[0][0]}{parts[1][0]}".upper()
        elif len(parts) == 1 and len(parts[0]) >= 2:
            initials = parts[0][:2].upper()
        elif len(parts) == 1:
            initials = parts[0][0].upper()
        else:
            initials = "U"

        font_size = max(10, int(size * 0.36))
        font = QFont("Segoe UI", font_size, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRect(0, 0, size, size), Qt.AlignCenter, initials)

    # Subtle rounded outer border ring
    painter.setClipping(False)
    painter.setPen(QPen(QColor("#CBD5E1"), 1.5))
    painter.drawRoundedRect(1, 1, size - 2, size - 2, radius, radius)
    painter.end()

    return pixmap

