"""Live fan curve preview and table-backed drag editor (no hardware writes)."""

from math import ceil, isfinite

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QColor, QPainter, QPen, QPalette
from PyQt6.QtWidgets import QWidget

from legion_linux.legion import (
    FANCURVE_MAX_TEMP_C,
    LEVEL_POINT_MIN,
    MAX_FAN_LEVEL,
    fan_level_to_rpm,
    fan_rpm_to_level,
)


class FanCurvePlot(QWidget):
    """Plot the table's effective speeds; edit only fields the table permits."""

    def __init__(self, entry_edits, parent=None):
        super().__init__(parent)
        self.entry_edits = entry_edits
        self.point_count = 0
        self.temperature_fields = set()
        self.has_fan_2_speed = False
        self.level_tables = None
        self.editable = False
        self._drag = None
        self._drag_original = None
        self.setMinimumSize(540, 290)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Fan curve preview and drag editor")

    def set_capabilities(self, point_count, temperature_fields, has_fan_2_speed, level_tables, editable):
        self.point_count = min(point_count, len(self.entry_edits))
        self.temperature_fields = temperature_fields
        self.has_fan_2_speed = has_fan_2_speed
        self.level_tables = level_tables
        self.editable = editable
        self._drag = None
        self._drag_original = None
        self.update()

    @property
    def temperature_axis(self):
        return {"cpu_upper_temp", "gpu_upper_temp"} <= self.temperature_fields

    def _rows(self):
        rows = []
        for view in self.entry_edits:
            try:
                rows.append(view.get())
            except ValueError:
                rows.append(None)  # Incomplete text must never become a control point.
        return rows

    def _writable_size(self, rows):
        size = min(self.point_count, len(rows))
        while size and rows[size - 1] is not None and rows[size - 1].is_empty():
            size -= 1
        return size

    def _speed(self, row, index, fan):
        if fan == 1 and not self.has_fan_2_speed:
            return None
        rpm = (row.fan1_speed, row.fan2_speed)[fan]
        if self.level_tables:
            table = self.level_tables[fan]
            if not table:
                return None
            # Shared WMI speed tables use fan 1's level for both fans.
            level = fan_rpm_to_level(
                row.fan1_speed if not self.has_fan_2_speed else rpm,
                index + 1,
                self.level_tables[0] if not self.has_fan_2_speed else table,
            )
            return level if level <= len(table) else None
        return rpm if isfinite(rpm) and rpm >= 0 else None

    def _bounds(self):
        return QRectF(72, 48, max(1, self.width() - 102), max(1, self.height() - 150))

    def _maximum(self, rows):
        if self.level_tables:
            return MAX_FAN_LEVEL
        values = [
            self._speed(row, index, fan)
            for index, row in enumerate(rows[: self._writable_size(rows)])
            if row
            for fan in range(2)
        ]
        highest = max([1] + [value for value in values if value is not None])
        scaled = highest * 1.15
        return scaled if isfinite(scaled) else highest

    def _temperature_range(self, rows):
        if not self.temperature_axis:
            return 0, FANCURVE_MAX_TEMP_C
        values = []
        for row in rows[: self._writable_size(rows)]:
            if row is not None:
                for name in ("cpu_lower_temp", "cpu_upper_temp", "gpu_lower_temp", "gpu_upper_temp"):
                    if name not in self.temperature_fields:
                        continue
                    value = getattr(row, name)
                    if 0 <= value <= FANCURVE_MAX_TEMP_C:
                        values.append(value)
        if not values:
            return 0, FANCURVE_MAX_TEMP_C
        # Zoom to configured temperatures, leaving room to drag either direction.
        return max(0, min(values) - 15), min(FANCURVE_MAX_TEMP_C, max(values) + 15)

    def _x(self, temperature, area, domain):
        return area.left() + area.width() * (temperature - domain[0]) / max(1, domain[1] - domain[0])

    def _position(self, row, index, fan, maximum, domain=None):
        speed = self._speed(row, index, fan)
        if speed is None:
            return None
        area = self._bounds()
        if self.temperature_axis:
            if domain is None:
                domain = self._temperature_range(self._rows())
            temperature = (row.cpu_upper_temp, row.gpu_upper_temp)[fan]
            if not 0 <= temperature <= FANCURVE_MAX_TEMP_C:
                return None
            x = self._x(temperature, area, domain)
        else:
            x = area.left() + area.width() * (index / (self.point_count - 1) if self.point_count > 1 else 0.5)
        y = area.bottom() - area.height() * min(speed, maximum) / maximum
        return x, y

    def _colors(self):
        dark = self.palette().color(QPalette.ColorRole.Window).lightness() < 128
        if dark:
            return QColor("#6bb9f3"), QColor("#ffb277")
        return QColor("#287fc0"), QColor("#d77630")

    def _paint_y_ticks(self, painter, area, maximum, muted):
        step = 1 if self.level_tables else (1000 if maximum > 3500 else 500 if maximum > 1600 else 250)
        values = (
            [maximum * index / 5 for index in range(6)]
            if maximum > 100_000
            else range(0, int(maximum // step) * step + 1, step)
        )
        grid = QColor(muted)
        grid.setAlpha(48)
        for value in values:
            y = area.bottom() - area.height() * value / maximum
            painter.setPen(QPen(grid, 1, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(area.left(), y), QPointF(area.right(), y))
            painter.setPen(muted)
            label = f"{value:.2g}" if value > 1_000_000 else f"{round(value):,}"
            painter.drawText(10, int(y + 5), label)

    def _x_ticks(self, domain):
        if self.temperature_axis:
            return range(5 * ceil(domain[0] / 5), domain[1] + 1, 5)
        return range(1, self.point_count + 1)

    def _paint_x_ticks(self, painter, area, domain, muted):
        grid = QColor(muted)
        grid.setAlpha(45)
        for tick in self._x_ticks(domain):
            x = (
                self._x(tick, area, domain)
                if self.temperature_axis
                else (area.left() + area.width() * (tick - 1) / max(1, self.point_count - 1))
            )
            painter.setPen(QPen(grid, 1, Qt.PenStyle.DotLine))
            painter.drawLine(QPointF(x, area.top()), QPointF(x, area.bottom()))
            painter.setPen(muted)
            label = f"{tick}°" if self.temperature_axis else str(tick)
            stagger = self.temperature_axis and area.width() * 5 / max(1, domain[1] - domain[0]) < 36
            y = area.bottom() + 19 + (16 if stagger and (tick // 5) % 2 else 0)
            painter.drawText(int(x - painter.fontMetrics().horizontalAdvance(label) / 2), int(y), label)

    def _paint_axes(self, painter, area, maximum, domain, muted):
        painter.save()
        self._paint_y_ticks(painter, area, maximum, muted)
        self._paint_x_ticks(painter, area, domain, muted)
        caption = "TEMPERATURE (°C)" if self.temperature_axis else "POINT ID (NO WRITABLE TEMPERATURES)"
        painter.setPen(muted)
        painter.drawText(int(area.center().x() - 110), self.height() - 10, caption)
        painter.restore()

    def _paint_legend(self, painter, colors, muted, area):
        painter.save()
        painter.setPen(muted)
        painter.drawText(18, 28, "FIRMWARE LEVEL" if self.level_tables else "FAN SPEED  ·  RPM")
        for fan, color in enumerate(colors):
            if fan == 1 and not self.has_fan_2_speed:
                continue
            x = area.right() - (190 if fan == 0 else 83)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.setPen(QPen(color, 2))
            painter.drawEllipse(QRectF(x, 18, 10, 10))
            painter.setPen(muted)
            legend = "Both fans (shared level)" if self.level_tables and not self.has_fan_2_speed else f"Fan {fan + 1}"
            painter.drawText(int(x + 16), 28, legend)
        painter.restore()

    def _lower_position(self, row, index, fan, point, domain):
        lower_field = ("cpu_lower_temp", "gpu_lower_temp")[fan]
        if not self.editable or lower_field not in self.temperature_fields:
            return None
        lower_edit = getattr(self.entry_edits[index], f"{lower_field}_edit")
        lower = getattr(row, lower_field)
        if not lower_edit.isEnabled() or not 0 <= lower <= FANCURVE_MAX_TEMP_C:
            return None
        return self._x(lower, self._bounds(), domain), point[1] + 12

    def _paint_band(self, painter, area, row, index, fan, color, y, x, domain):
        lower_field = ("cpu_lower_temp", "gpu_lower_temp")[fan]
        if not self.temperature_axis or lower_field not in self.temperature_fields:
            return
        lower = getattr(row, lower_field)
        if not 0 <= lower <= FANCURVE_MAX_TEMP_C:
            return
        start = self._x(lower, area, domain)
        band = QColor(color)
        band.setAlpha(65)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(band)
        painter.drawRect(QRectF(min(start, x), y - 6, max(6, abs(x - start)), 12))
        # Square handle: lower temperature is independently draggable.
        if self._lower_position(row, index, fan, (x, y), domain):
            painter.setPen(QPen(color, 2))
            painter.setBrush(self.palette().color(QPalette.ColorRole.Base))
            painter.drawRect(QRectF(start - 4.5, y + 8, 9, 9))

    def _paint_series(self, painter, area, rows, size, maximum, domain, colors):
        for fan, color in enumerate(colors):
            if fan == 1 and not self.has_fan_2_speed:
                continue
            previous = None
            for index, row in enumerate(rows[:size]):
                if row is None:
                    previous = None
                    continue
                try:
                    point = self._position(row, index, fan, maximum, domain)
                except ValueError:
                    point = None
                if point is None:
                    previous = None
                    continue
                x, y = point
                self._paint_band(painter, area, row, index, fan, color, y, x, domain)
                if previous is not None:
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.setPen(QPen(color, 3))
                    painter.drawLine(previous, QPointF(x, y))
                painter.setPen(QPen(color, 2))
                painter.setBrush(color)
                painter.drawEllipse(QRectF(x - 5.5, y - 5.5, 11, 11))
                previous = QPointF(x, y)

    def _paint_padding(self, painter, area, rows, size, muted):
        padding = [
            index for index in range(size, self.point_count) if rows[index] is not None and rows[index].is_empty()
        ]
        if not padding:
            return
        painter.save()
        painter.setPen(muted)
        painter.drawText(int(area.left()), int(area.bottom() + 66), "TRIMMED ON WRITE")
        for offset, index in enumerate(padding):
            x = area.left() + 143 + offset * 32
            y = area.bottom() + 62
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QRectF(x - 4, y - 4, 8, 8))
            painter.drawLine(QPointF(x - 2, y - 2), QPointF(x + 2, y + 2))
            painter.drawText(int(x + 7), int(y + 4), str(index + 1))
        painter.restore()

    def paintEvent(self, event):  # pylint: disable=invalid-name,unused-argument
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        base = self.palette().color(QPalette.ColorRole.Base)
        muted = self.palette().color(QPalette.ColorRole.Text)
        muted.setAlpha(170)
        border = self.palette().color(QPalette.ColorRole.Mid)
        border.setAlpha(100)
        painter.setPen(QPen(border, 1))
        painter.setBrush(base)
        painter.drawRect(QRectF(2, 2, self.width() - 4, self.height() - 4))
        area = self._bounds()
        rows = self._rows()
        size = self._writable_size(rows)
        maximum = self._drag[2] if self._drag else self._maximum(rows)
        domain = self._drag[3] if self._drag else self._temperature_range(rows)
        colors = self._colors()
        self._paint_axes(painter, area, maximum, domain, muted)
        self._paint_legend(painter, colors, muted, area)
        if not self.point_count:
            painter.setPen(muted)
            painter.drawText(area.toRect(), Qt.AlignmentFlag.AlignCenter, "No writable fan curve points")
            return
        self._paint_series(painter, area, rows, size, maximum, domain, colors)
        self._paint_padding(painter, area, rows, size, muted)
        self._paint_selection(painter, area, rows, maximum, domain, colors)

    def _paint_selection(self, painter, area, rows, maximum, domain, colors):
        if self._drag is None:
            return
        index, fan, _, _, handle = self._drag
        row = rows[index]
        if row is None:
            return
        point = self._position(row, index, fan, maximum, domain)
        if point is None:
            return
        color = colors[fan]
        painter.save()
        painter.setPen(QPen(color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        anchor = point
        if handle == "lower":
            prefix = ("cpu", "gpu")[fan]
            anchor = (self._x(getattr(row, f"{prefix}_lower_temp"), area, domain), point[1] + 12)
            painter.drawRect(QRectF(anchor[0] - 9, anchor[1] - 9, 18, 18))
        else:
            painter.drawEllipse(QRectF(point[0] - 10, point[1] - 10, 20, 20))
        level = self._speed(row, index, fan)
        rpm = (
            fan_level_to_rpm(level, self.level_tables[fan])
            if self.level_tables
            else (row.fan1_speed, row.fan2_speed)[fan]
        )
        label = f"L{level} · {rpm:,.0f} RPM" if self.level_tables else f"{rpm:,.0f} RPM"
        if self.temperature_axis:
            prefix = ("cpu", "gpu")[fan]
            if f"{prefix}_lower_temp" in self.temperature_fields:
                label += f" · {getattr(row, f'{prefix}_lower_temp')}–{getattr(row, f'{prefix}_upper_temp')}°C"
            else:
                label += f" · {getattr(row, f'{prefix}_upper_temp')}°C"
        width = painter.fontMetrics().horizontalAdvance(label) + 20
        x = max(area.left(), min(area.right() - width, anchor[0] + 12))
        y = anchor[1] - 42 if anchor[1] > area.top() + 46 else anchor[1] + 15
        y = min(area.bottom() - 27, y)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawRect(QRectF(x, y, width, 26))
        painter.setPen(
            QColor("#16212c") if self.palette().color(QPalette.ColorRole.Window).lightness() < 128 else QColor("white")
        )
        painter.drawText(int(x + 10), int(y + 18), label)
        painter.restore()

    def _nearest(self, position, rows, maximum, domain, writable_only=True):
        nearest = None
        distance = 13 * 13
        for index, row in enumerate(rows[: self._writable_size(rows)]):
            if row is None:
                continue
            for fan in range(2):
                speed_edit = (self.entry_edits[index].fan_speed1_edit, self.entry_edits[index].fan_speed2_edit)[fan]
                if writable_only and not speed_edit.isEnabled():
                    continue
                try:
                    point = self._position(row, index, fan, maximum, domain)
                except ValueError:
                    continue
                if point:
                    squared = (point[0] - position.x()) ** 2 + (point[1] - position.y()) ** 2
                    if squared < distance:
                        distance, nearest = squared, (index, fan, "point")
                    lower_handle = self._lower_position(row, index, fan, point, domain)
                    if lower_handle:
                        squared = (lower_handle[0] - position.x()) ** 2 + (lower_handle[1] - position.y()) ** 2
                        if squared < distance:
                            distance, nearest = squared, (index, fan, "lower")
        return nearest

    def mousePressEvent(self, event):  # pylint: disable=invalid-name
        if event.button() != Qt.MouseButton.LeftButton or not self.editable:
            return
        rows = self._rows()
        maximum = self._maximum(rows)
        domain = self._temperature_range(rows)
        nearest = self._nearest(event.position(), rows, maximum, domain)
        if nearest is not None:
            self._drag = (nearest[0], nearest[1], maximum, domain, nearest[2])
            self._drag_original = {field: field.text() for field in self.entry_edits[nearest[0]].edits}
            self.setFocus()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.update()
            event.accept()

    def _snapped_speed(self, index, fan, position, area, maximum):
        value = (area.bottom() - position.y()) * maximum / area.height()
        if not self.level_tables:
            return round(max(0, min(maximum, value))), None
        table = self.level_tables[fan]
        if not table or len(table) < LEVEL_POINT_MIN[index]:
            return None, None
        ceiling = len(table)
        if not self.has_fan_2_speed:
            other = self.level_tables[1]
            if not other or len(other) < LEVEL_POINT_MIN[index]:
                return None, None
            ceiling = min(ceiling, len(other))
        level = max(LEVEL_POINT_MIN[index], min(ceiling, round(value)))
        return fan_level_to_rpm(level, table), level

    @staticmethod
    def _target_temperature(position, area, domain):
        return round(domain[0] + (position.x() - area.left()) * (domain[1] - domain[0]) / area.width())

    def _move_temperature(self, view, fan, position, area, domain):
        if not self.temperature_axis:
            return
        prefix = ("cpu", "gpu")[fan]
        upper = getattr(view, f"{prefix}_upper_temp_edit")
        if not upper.isEnabled():
            return
        target = self._target_temperature(position, area, domain)
        lower = getattr(view, f"{prefix}_lower_temp_edit")
        if lower.isEnabled():
            try:
                span = int(self._drag_original[upper]) - int(self._drag_original[lower])
            except ValueError:
                return
            if not 0 <= span <= FANCURVE_MAX_TEMP_C:
                return
            new_lower = max(0, min(FANCURVE_MAX_TEMP_C - span, target - span))
            lower.setText(str(new_lower))
            upper.setText(str(new_lower + span))
        else:
            upper.setText(str(max(0, min(FANCURVE_MAX_TEMP_C, target))))

    def _move_lower(self, view, fan, position, area, domain):
        prefix = ("cpu", "gpu")[fan]
        lower = getattr(view, f"{prefix}_lower_temp_edit")
        upper = getattr(view, f"{prefix}_upper_temp_edit")
        if not lower.isEnabled() or not upper.text().isdigit():
            return
        upper_value = int(upper.text())
        if not 0 <= upper_value <= FANCURVE_MAX_TEMP_C:
            return
        target = self._target_temperature(position, area, domain)
        lower.setText(str(max(0, min(upper_value, target))))

    def _move_point(self, position):
        if self._drag is None:
            return
        index, fan, maximum, domain, handle = self._drag
        area = self._bounds()
        view = self.entry_edits[index]
        if handle == "lower":
            self._move_lower(view, fan, position, area, domain)
            self.update()
            return
        speed, level = self._snapped_speed(index, fan, position, area, maximum)
        if speed is None:
            return
        speed_edit = (view.fan_speed1_edit, view.fan_speed2_edit)[fan]
        if speed_edit.isEnabled():
            speed_edit.setText(str(speed))
        if level is not None and not self.has_fan_2_speed:
            view.fan_speed2_edit.setText(str(fan_level_to_rpm(level, self.level_tables[1])))
        self._move_temperature(view, fan, position, area, domain)
        self.update()

    def _point_tooltip(self, row, index, fan, handle="point"):
        speed = self._speed(row, index, fan)
        rpm = (
            fan_level_to_rpm(speed, self.level_tables[fan])
            if self.level_tables
            else (row.fan1_speed, row.fan2_speed)[fan]
        )
        details = f"Point {index + 1} · Fan {fan + 1}: {rpm:g} RPM"
        if self.level_tables:
            details += f" (firmware level {speed})"
            if not self.has_fan_2_speed:
                details += f"\nFan 2: {fan_level_to_rpm(speed, self.level_tables[1])} RPM at the same level"
        prefix = ("cpu", "gpu")[fan]
        if f"{prefix}_upper_temp" in self.temperature_fields:
            upper = getattr(row, f"{prefix}_upper_temp")
            if f"{prefix}_lower_temp" in self.temperature_fields:
                details += f"\n{prefix.upper()} {getattr(row, f'{prefix}_lower_temp')}–{upper}°C"
            else:
                details += f"\n{prefix.upper()} upper {upper}°C"
        writable = (self.entry_edits[index].fan_speed1_edit, self.entry_edits[index].fan_speed2_edit)[fan].isEnabled()
        if handle == "lower":
            return details + "\nDrag the square to change only the lower temperature"
        if not writable:
            return details + "\nShared fan speed (read-only)"
        if self.temperature_axis:
            action = "shift both bounds" if f"{prefix}_lower_temp" in self.temperature_fields else "change upper temp"
            return details + f"\nDrag the dot to {action} and edit speed"
        return details + "\nDrag the dot to edit speed"

    def mouseMoveEvent(self, event):  # pylint: disable=invalid-name
        if self._drag is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self._move_point(event.position())
        elif self.editable and self._drag is None:
            rows = self._rows()
            nearest = self._nearest(event.position(), rows, self._maximum(rows), self._temperature_range(rows), False)
            if nearest is None:
                self.unsetCursor()
                self.setToolTip("")
            else:
                index, fan, handle = nearest
                writable = (self.entry_edits[index].fan_speed1_edit, self.entry_edits[index].fan_speed2_edit)[fan]
                self.setCursor(
                    Qt.CursorShape.OpenHandCursor
                    if handle == "lower" or writable.isEnabled()
                    else Qt.CursorShape.ArrowCursor
                )
                self.setToolTip(self._point_tooltip(rows[index], index, fan, handle))

    def mouseReleaseEvent(self, event):  # pylint: disable=invalid-name
        if self._drag is not None and event.button() == Qt.MouseButton.LeftButton:
            self._move_point(event.position())
            self._drag = None
            self._drag_original = None
            self.unsetCursor()
            self.update()
            event.accept()

    def keyPressEvent(self, event):  # pylint: disable=invalid-name
        if self._drag is not None and event.key() == Qt.Key.Key_Escape:
            for field, original in self._drag_original.items():
                if field.text() != original:
                    field.setText(original)
            self._drag = None
            self._drag_original = None
            self.unsetCursor()
            self.update()
            event.accept()
        else:
            super().keyPressEvent(event)
