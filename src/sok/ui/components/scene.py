# ===----------------------------------------------------------------------=== #
#
# This source file is part of the S.O.K open source project
#
# Copyright (c) 2026 S.O.K Team
# Licensed under the MIT License
#
# See LICENSE for license information
#
# ===----------------------------------------------------------------------=== #
"""
The scene: the selected item shown large, lit by its own color.

The signature of the SOKTeam art direction. The poster, cover or book stands
on a dark stage, with a glow of its dominant color, a shadow on the floor and
the same color as a faint ambient light from the top. Below it: the title, a
muted line, a sheet of details joined by dotted leaders, the final path
("Will be stored here") and the actions, as small keys.
"""

from dataclasses import dataclass, field
from enum import Enum

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QFontMetrics,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
    QTextOption,
)
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from sok.ui.components.base import KeyButton, parse_color
from sok.ui.components.media_visual import (
    dominant_color,
    rounded,
    standin_colors,
    standin_pixmap,
)
from sok.ui.theme import Theme, ui_font
from sok.ui.tokens import RADIUS


class Shape(Enum):
    """How the item stands on the scene."""

    POSTER = "poster"  # 2:3, movies and TV shows
    COVER = "cover"  # square, music
    BOOK = "book"  # 2:3 with a spine


SIZES = {
    Shape.POSTER: QSize(228, 342),
    Shape.COVER: QSize(280, 280),
    Shape.BOOK: QSize(220, 330),
}

# Opacities from the art direction: glow 0.3, ambient light 0.16.
GLOW_ALPHA = 0.30
AMBIENT_ALPHA = 0.16


@dataclass
class SceneItem:
    """What the scene shows.

    Attributes:
        title: Title under the object.
        subtitle: Muted line ("2024 · Denis Villeneuve").
        image: Poster or cover; None draws the stand-in.
        year: Year written on the stand-in.
        shape: Poster, cover or book.
        fields: (label, value) rows of the dotted sheet.
        destination: Final path, under "Will be stored here" ("" hides it).
        warning: Sentence in the caution color when S.O.K does not know.
    """

    title: str
    subtitle: str = ""
    image: QPixmap | None = None
    year: str = ""
    shape: Shape = Shape.POSTER
    fields: list[tuple[str, str]] = field(default_factory=list)
    destination: str = ""
    warning: str = ""


SHADOW_BLUR = 80
_shadows: dict[tuple[int, int, int, int], QImage] = {}


def _soft_shadow(size: QSize, radius: float, color: QColor) -> QImage:
    """Return the blurred shadow of a rounded rectangle, with SHADOW_BLUR of margin.

    The shape is drawn, shrunk twenty times and enlarged back with smooth
    scaling: a soft blur without a blur effect. Results are kept by size and
    color.
    """
    key = (size.width(), size.height(), int(radius), color.rgba())
    if key not in _shadows:
        pad = SHADOW_BLUR
        image = QImage(
            size.width() + 2 * pad,
            size.height() + 2 * pad,
            QImage.Format.Format_ARGB32_Premultiplied,
        )
        image.fill(Qt.GlobalColor.transparent)
        p = QPainter(image)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawRoundedRect(QRectF(pad, pad, size.width(), size.height()), radius, radius)
        p.end()
        smooth = Qt.TransformationMode.SmoothTransformation
        small = image.scaled(
            image.width() // 20,
            image.height() // 20,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            smooth,
        )
        middle = small.scaled(
            image.width() // 2,
            image.height() // 2,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            smooth,
        )
        _shadows[key] = middle.scaled(
            image.size(), Qt.AspectRatioMode.IgnoreAspectRatio, smooth
        )
    return _shadows[key]


def _palette(widget: QWidget) -> dict[str, str]:
    return getattr(widget.window(), "c", None) or Theme.DARK


def _with_alpha(color: QColor, alpha: float) -> QColor:
    out = QColor(color)
    out.setAlphaF(alpha)
    return out


def paint_light(p: QPainter, rect: QRectF, color: QColor, obj: QRectF) -> None:
    """The light of a scene: ambient light of the object's color from the
    top, and its glow around the object.

    Args:
        p: Painter of the scene.
        rect: Rectangle of the scene.
        color: Dominant color of the object.
        obj: Rectangle of the object in the scene.
    """
    # Ambient light (CSS: radial gradient at 50% 22%, fading out at 72%).
    center = QPointF(rect.width() / 2, rect.height() * 0.22)
    light = QRadialGradient(center, max(rect.width(), 420) * 0.72)
    light.setColorAt(0, _with_alpha(color, AMBIENT_ALPHA))
    light.setColorAt(1, _with_alpha(color, 0))
    p.fillRect(rect, light)
    # Glow around the object, 50px lower (CSS: 0 50px 110px, opacity 0.3).
    glow = QRadialGradient(obj.center() + QPointF(0, 50), obj.height() * 0.62)
    glow.setColorAt(0, _with_alpha(color, GLOW_ALPHA))
    glow.setColorAt(1, _with_alpha(color, 0))
    p.fillRect(rect, glow)


class _Stage(QWidget):
    """The object on the floor: glow, shadows, the visual and its edges."""

    FLOOR_GAP = 18

    def __init__(self, parent=None):
        super().__init__(parent)
        self._item: SceneItem | None = None
        self._visual: QPixmap | None = None
        self._color = QColor(128, 128, 128)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_item(self, item: SceneItem | None, color: QColor) -> None:
        self._item = item
        self._color = color
        self._visual = None
        size = SIZES[item.shape] if item else QSize(0, 0)
        self.setFixedHeight(size.height() + self.FLOOR_GAP + 18 if item else 0)
        self.update()

    def object_rect(self) -> QRectF:
        """Rectangle of the poster, cover or book in this widget."""
        if not self._item:
            return QRectF()
        size = SIZES[self._item.shape]
        return QRectF((self.width() - size.width()) / 2, 0, size.width(), size.height())

    def _object(self) -> QPixmap:
        assert self._item is not None
        size = SIZES[self._item.shape]
        if self._visual is None:
            ratio = self.devicePixelRatioF()
            source = self._item.image or standin_pixmap(
                self._item.title, self._item.year, size.width(), size.height(), ratio
            )
            radius = 6 if self._item.shape == Shape.BOOK else RADIUS["poster"]
            self._visual = rounded(source, size.width(), size.height(), radius)
        return self._visual

    def paintEvent(self, e):  # noqa: N802 - Qt API
        if not self._item:
            return
        size = SIZES[self._item.shape]
        x = (self.width() - size.width()) / 2
        rect = QRectF(x, 0, size.width(), size.height())
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)

        # The glow of its own color is drawn by the Scene, behind this widget,
        # so that its edges are not cut.

        # Floor shadow: a flat oval under the object.
        floor = QRectF(
            rect.center().x() - (size.width() - 28) / 2,
            rect.bottom() + self.FLOOR_GAP,
            size.width() - 28,
            18,
        )
        shadow = QRadialGradient(floor.center(), floor.width() / 2)
        shadow.setColorAt(0, QColor(0, 0, 0, 217))
        shadow.setColorAt(1, QColor(0, 0, 0, 0))
        p.save()
        p.translate(floor.center())
        p.scale(1, floor.height() / floor.width())
        p.translate(-floor.center())
        p.setBrush(shadow)
        p.drawEllipse(floor.center(), floor.width() / 2, floor.width() / 2)
        p.restore()

        # Drop shadow of the theme (CSS: 0 20px 40px), blurred once.
        radius = 6 if self._item.shape == Shape.BOOK else RADIUS["poster"]
        c = _palette(self)
        shadow_image = _soft_shadow(size, radius, parse_color(c["shadow-poster-drop"]))
        p.drawImage(
            rect.topLeft() + QPointF(-SHADOW_BLUR, 20 - SHADOW_BLUR), shadow_image
        )

        p.drawPixmap(rect.topLeft(), self._object())

        path = QPainterPath()
        path.addRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 31), 1))
        p.drawPath(path)
        # Light from above: a 1px line inside the top edge.
        p.setPen(QPen(QColor(255, 255, 255, 64), 1))
        p.drawLine(
            QPointF(rect.left() + radius, rect.top() + 1.5),
            QPointF(rect.right() - radius, rect.top() + 1.5),
        )

        if self._item.shape == Shape.BOOK:
            # The spine: a darker band and a fold line at the left.
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, 70))
            spine = QPainterPath()
            spine.addRoundedRect(
                QRectF(rect.left(), rect.top(), 12, rect.height()), radius, radius
            )
            p.drawPath(spine)
            p.setPen(QPen(QColor(255, 255, 255, 40), 1))
            p.drawLine(
                QPointF(rect.left() + 12.5, rect.top() + 1),
                QPointF(rect.left() + 12.5, rect.bottom() - 1),
            )
        p.end()


class _Sheet(QWidget):
    """Details aligned with dotted leaders, like a library card."""

    ROW = 25

    def __init__(self, parent=None):
        super().__init__(parent)
        self._fields: list[tuple[str, str]] = []
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_fields(self, fields: list[tuple[str, str]]) -> None:
        self._fields = fields
        self.setFixedHeight(max(0, len(fields) * self.ROW - 4))
        self.setVisible(bool(fields))
        self.update()

    def paintEvent(self, e):  # noqa: N802 - Qt API
        c = _palette(self)
        label_font, value_font = ui_font(14), ui_font(13, 400, mono=True)
        p = QPainter(self)
        for i, (label, value) in enumerate(self._fields):
            baseline = i * self.ROW + 15
            p.setFont(label_font)
            p.setPen(parse_color(c["ink-muted"]))
            p.drawText(0, baseline, label)
            label_w = QFontMetrics(label_font).horizontalAdvance(label)
            value_w = QFontMetrics(value_font).horizontalAdvance(value)
            p.setFont(value_font)
            p.setPen(parse_color(c["ink"]))
            p.drawText(self.width() - value_w, baseline, value)
            # Dotted leader between them, 4px above the baseline.
            pen = QPen(parse_color(c["line-strong"]), 1, Qt.PenStyle.CustomDashLine)
            pen.setDashPattern([1, 2])
            p.setPen(pen)
            y = baseline - 4 + 0.5
            start, end = label_w + 8, self.width() - value_w - 8
            if end > start:
                p.drawLine(QPointF(start, y), QPointF(end, y))
        p.end()


class _Path(QWidget):
    """A path in Geist Mono, wrapped at spaces, or anywhere if a part is too
    long."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._text = ""
        self._font = ui_font(13, 400, mono=True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def setText(self, text: str) -> None:  # noqa: N802 - Qt API
        self._text = text
        self.updateGeometry()
        self.update()

    def hasHeightForWidth(self) -> bool:  # noqa: N802 - Qt API
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802 - Qt API
        fm = QFontMetrics(self._font)
        rect = fm.boundingRect(
            0, 0, max(1, width), 10_000, int(Qt.TextFlag.TextWordWrap), self._text
        )
        return max(19, rect.height())

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt API
        return QSize(200, self.heightForWidth(self.width() or 360))

    def paintEvent(self, e):  # noqa: N802 - Qt API
        c = _palette(self)
        p = QPainter(self)
        p.setFont(self._font)
        p.setPen(parse_color(c["ink"]))
        option = QTextOption()
        option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        p.drawText(QRectF(self.rect()), self._text, option)
        p.end()


class Scene(QWidget):
    """The right column of a media screen, showing the selected item.

    Add the actions of the item with add_action(); they are small keys,
    centered under the details.
    """

    def __init__(self, destination_label: str = "Will be stored here", parent=None):
        """Build an empty scene.

        Args:
            destination_label: Translated text above the final path.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setObjectName("Scene")
        self.setMinimumWidth(360)
        self._item: SceneItem | None = None
        self._color = QColor(128, 128, 128)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(44, 72, 44, 36)
        layout.setSpacing(36)

        self._stage = _Stage()
        layout.addWidget(self._stage)

        details = QVBoxLayout()
        details.setSpacing(22)
        layout.addLayout(details)

        heading = QVBoxLayout()
        heading.setSpacing(6)
        self._title = QLabel()
        title_font = ui_font(30, 650)
        title_font.setLetterSpacing(title_font.SpacingType.AbsoluteSpacing, -1.05)
        self._title.setFont(title_font)
        self._subtitle = QLabel()
        self._subtitle.setFont(ui_font(16))
        for label in (self._title, self._subtitle):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setWordWrap(True)
            heading.addWidget(label)
        details.addLayout(heading)

        self._warning = QLabel()
        self._warning.setFont(ui_font(15, 500))
        self._warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._warning.setWordWrap(True)
        details.addWidget(self._warning)

        # A widget of the page, such as the episodes of a series.
        self._extra_slot = QVBoxLayout()
        self._extra_slot.setContentsMargins(0, 0, 0, 0)
        details.addLayout(self._extra_slot)
        self._extra: QWidget | None = None

        self._sheet = _Sheet()
        details.addWidget(self._sheet)

        self._destination = QWidget()
        dest_layout = QVBoxLayout(self._destination)
        dest_layout.setContentsMargins(0, 18, 0, 0)
        dest_layout.setSpacing(6)
        self._destination_label = QLabel(destination_label)
        self._destination_label.setFont(ui_font(13))
        self._path = _Path()
        dest_layout.addWidget(self._destination_label)
        dest_layout.addWidget(self._path)
        details.addWidget(self._destination)

        self._actions = QHBoxLayout()
        self._actions.setSpacing(10)
        self._actions.addStretch()
        self._actions.addStretch()
        details.addLayout(self._actions)
        layout.addStretch()

        self.set_item(None)

    @property
    def color(self) -> QColor:
        """Dominant color of the item, used for its light."""
        return self._color

    def set_extra(self, widget: QWidget | None) -> None:
        """Show a widget of the page between the title and the details."""
        if self._extra is not None:
            self._extra_slot.removeWidget(self._extra)
            self._extra.deleteLater()
        self._extra = widget
        if widget is not None:
            self._extra_slot.addWidget(widget)

    def set_destination_label(self, text: str) -> None:
        self._destination_label.setText(text)

    def add_action(self, text: str = "") -> KeyButton:
        """Add a small key under the details and return it."""
        button = KeyButton(text, small=True)
        self._actions.insertWidget(self._actions.count() - 1, button)
        return button

    def set_item(self, item: SceneItem | None) -> None:
        """Show an item, or nothing."""
        self._item = item
        if item is None:
            self._color = QColor(128, 128, 128)
        elif item.image is not None:
            self._color = dominant_color(item.image)
        else:
            self._color = standin_colors(item.title)[0]
        self._stage.set_item(item, self._color)
        self._title.setText(item.title if item else "")
        self._subtitle.setText(item.subtitle if item else "")
        self._subtitle.setVisible(bool(item and item.subtitle))
        self._warning.setText(item.warning if item else "")
        self._warning.setVisible(bool(item and item.warning))
        self._sheet.set_fields(item.fields if item else [])
        self._path.setText(item.destination if item else "")
        self._destination.setVisible(bool(item and item.destination))
        for i in range(self._actions.count()):
            widget = self._actions.itemAt(i).widget()
            if widget:
                widget.setVisible(item is not None)
        self._restyle()
        self.update()

    def _restyle(self) -> None:
        c = _palette(self)
        # Transparent, so that the light of the scene shows behind the texts.
        for label, role in (
            (self._title, "ink"),
            (self._subtitle, "ink-muted"),
            (self._warning, "caution"),
            (self._destination_label, "ink-muted"),
        ):
            label.setStyleSheet(f"color: {c[role]}; background: transparent;")
        self._destination.setStyleSheet("background: transparent;")

    def changeEvent(self, e):  # noqa: N802 - Qt API
        super().changeEvent(e)
        if e.type() in (e.Type.StyleChange, e.Type.PaletteChange):
            self._restyle()

    def paintEvent(self, e):  # noqa: N802 - Qt API
        c = _palette(self)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        p.fillRect(rect, parse_color(c["bg"]))
        if self._item:
            obj = self._stage.object_rect().translated(QPointF(self._stage.pos()))
            paint_light(p, rect, self._color, obj)
        # A hairline separates the scene from the list.
        p.setPen(QPen(parse_color(c["line"]), 1))
        p.drawLine(QPointF(0.5, 0), QPointF(0.5, rect.height()))
        p.end()

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt API
        return QSize(460, 900)
