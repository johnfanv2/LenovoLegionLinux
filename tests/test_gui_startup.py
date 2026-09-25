"""Run with QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -p test_gui_startup.py."""

import logging
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python/legion_linux"))

from PyQt6.QtCore import QEvent, QPointF, Qt
from PyQt6.QtGui import QColor, QIcon, QKeyEvent, QMouseEvent, QPalette
from PyQt6.QtWidgets import QApplication, QMessageBox
from legion_linux import legion
from legion_linux.legion import FanCurve, FanCurveEntry, FanCurveIO, FileFeature
from legion_linux.legion_gui import FanCurveTab, LegionController, MainWindow, PresetTrayController


class GuiStartupTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        logging.disable(logging.CRITICAL)

    def check_startup(self, hwmon_path, read_from_hw, supported):
        with patch.object(FanCurveIO, "_find_hwmon_dir", return_value=hwmon_path), patch.object(
            FileFeature,
            "_write_file",
            side_effect=AssertionError("Startup must not write to hardware"),
        ):
            controller = LegionController(
                self.app,
                expect_hwmon=hwmon_path is not None,
                use_legion_cli_to_write=True,
            )
            window = MainWindow(controller, QIcon())
            try:
                with patch.object(controller.model, "read_fancurve_from_hw") as read_curve:
                    controller.init(read_from_hw=read_from_hw)
                    self.assertEqual(read_curve.call_count, int(supported and read_from_hw))
                self.assertEqual(controller.view_fancurve.load_button.isEnabled(), supported)
                self.assertEqual(controller.view_fancurve.write_button.isEnabled(), supported)
                if hwmon_path and not supported:
                    self.assertIn("not supported", controller.view_fancurve.note_label2.text())
            finally:
                window.deleteLater()
                self.app.processEvents()

    def make_plot(self, entries, *, point_count=10, temperatures=(), fan2=True, tables=None):
        controller = Mock()
        controller.model.fancurve_io.has_acceleration_curve.return_value = False
        tab = FanCurveTab(controller)
        tab.curve_plot.resize(680, 245)
        tab.set_fancurve(
            FanCurve("test", entries),
            False,
            True,
            has_fan_2_speed=fan2,
            temperature_fields=set(temperatures),
            has_acceleration_curve=False,
            point_count=point_count,
            level_tables=tables,
        )
        return controller, tab, tab.curve_plot

    @staticmethod
    def curve_entry(fan1=2000, fan2=2500, cpu_lower=45, cpu_upper=70, gpu_lower=50, gpu_upper=75):
        return FanCurveEntry(fan1, fan2, cpu_lower, cpu_upper, gpu_lower, gpu_upper, 0, 0, 0, 0)

    def drag_point(self, plot, index, fan, x, y, *, lower=False):
        rows = plot._rows()
        old = plot._position(rows[index], index, fan, plot._maximum(rows))
        if lower:
            prefix = ("cpu", "gpu")[fan]
            temperature = getattr(rows[index], f"{prefix}_lower_temp")
            old = (plot._x(temperature, plot._bounds(), plot._temperature_range(rows)), old[1] + 12)
        for kind, position, buttons in (
            (QEvent.Type.MouseButtonPress, QPointF(*old), Qt.MouseButton.LeftButton),
            (QEvent.Type.MouseMove, QPointF(x, y), Qt.MouseButton.LeftButton),
            (QEvent.Type.MouseButtonRelease, QPointF(x, y), Qt.MouseButton.NoButton),
        ):
            event = QMouseEvent(kind, position, Qt.MouseButton.LeftButton, buttons, Qt.KeyboardModifier.NoModifier)
            self.app.sendEvent(plot, event)

    def test_plot_updates_from_table_and_trims_only_trailing_empty_rows(self):
        controller, tab, plot = self.make_plot([self.curve_entry()] * 8, fan2=False)
        try:
            self.assertEqual(plot._writable_size(plot._rows()), 8)
            self.assertTrue(tab.entry_edits[8].fan_speed1_edit.isEnabled())
            with patch.object(plot, "update") as update:
                tab.entry_edits[1].fan_speed1_edit.setText("3600")
                update.assert_called()
            self.assertEqual(plot._speed(plot._rows()[1], 1, 0), 3600)
            tab.entry_edits[1].fan_speed1_edit.setText("invalid")
            self.assertIsNone(plot._rows()[1])
            plot.grab()  # Partial numeric edits must not crash a repaint.
            self.assertEqual(plot._writable_size(plot._rows()), 8)
            self.assertIsNone(plot._drag)
            controller.on_write_fan_curve_to_hw.assert_not_called()
        finally:
            tab.deleteLater()

    def test_temperature_and_native_rpm_drag_only_edit_table(self):
        controller, tab, plot = self.make_plot(
            [self.curve_entry()],
            point_count=1,
            temperatures=FanCurveIO.temperature_files,
        )
        try:
            view = tab.entry_edits[0]
            self.assertTrue(plot.temperature_axis)
            area = plot._bounds()
            x = plot._x(90, area, plot._temperature_range(plot._rows()))
            self.drag_point(plot, 0, 0, x, area.bottom())
            self.assertEqual(view.fan_speed1_edit.text(), "0")  # Native RPM permits fan stop.
            self.assertEqual(view.cpu_upper_temp_edit.text(), "90")
            self.assertEqual(view.cpu_lower_temp_edit.text(), "65")
            self.assertEqual(view.gpu_upper_temp_edit.text(), "75")
            self.drag_point(plot, 0, 0, area.left() - area.width(), area.bottom())
            self.assertEqual(view.cpu_upper_temp_edit.text(), "25")  # Both bounds clamp while preserving their gap.
            self.assertEqual(view.cpu_lower_temp_edit.text(), "0")
            self.assertEqual(tab.get_fancurve().entries[0].fan1_speed, 0)
            controller.on_write_fan_curve_to_hw.assert_not_called()
        finally:
            tab.deleteLater()

    def test_lower_temperature_handle_moves_only_lower_bound(self):
        controller, tab, plot = self.make_plot(
            [self.curve_entry()], point_count=1, temperatures=FanCurveIO.temperature_files
        )
        try:
            view = tab.entry_edits[0]
            area = plot._bounds()
            x = plot._x(60, area, plot._temperature_range(plot._rows()))
            self.drag_point(plot, 0, 0, x, area.bottom(), lower=True)
            self.assertEqual(view.cpu_lower_temp_edit.text(), "60")
            self.assertEqual(view.cpu_upper_temp_edit.text(), "70")
            self.assertEqual(view.fan_speed1_edit.text(), "2000")
            self.assertEqual(view.gpu_lower_temp_edit.text(), "50")
            self.drag_point(plot, 0, 0, area.right(), area.bottom(), lower=True)
            self.assertEqual(view.cpu_lower_temp_edit.text(), "70")
            self.assertEqual(view.cpu_upper_temp_edit.text(), "70")
            controller.on_write_fan_curve_to_hw.assert_not_called()
        finally:
            tab.deleteLater()

    def test_upper_only_model_does_not_create_a_lower_temperature(self):
        _, tab, plot = self.make_plot(
            [self.curve_entry()], point_count=1, temperatures={"cpu_upper_temp", "gpu_upper_temp"}
        )
        try:
            view = tab.entry_edits[0]
            self.assertFalse(view.cpu_lower_temp_edit.isEnabled())
            x = plot._x(90, plot._bounds(), plot._temperature_range(plot._rows()))
            self.drag_point(plot, 0, 0, x, plot._bounds().bottom())
            self.assertEqual(view.cpu_upper_temp_edit.text(), "90")
            self.assertEqual(view.cpu_lower_temp_edit.text(), "45")
        finally:
            tab.deleteLater()

    def test_level_drag_uses_firmware_ladder_and_point_minima(self):
        table1 = [0, 900, 1800, 2400, 3000, 3500, 4000, 4500, 5000, 5500]
        table2 = [0, 1000, 1900, 2500, 3100, 3600, 4100, 4600, 5100, 5600]
        controller, tab, plot = self.make_plot(
            [
                self.curve_entry(fan1=3000, fan2=3100, cpu_lower=0, cpu_upper=0, gpu_lower=0, gpu_upper=0)
                for _ in range(10)
            ],
            fan2=False,
            tables=(table1, table2),
        )
        try:
            self.assertFalse(plot.temperature_axis)
            self.assertFalse(tab.entry_edits[8].fan_speed2_edit.isEnabled())
            self.assertIsNone(plot._speed(plot._rows()[0], 0, 1))  # One line for shared levels.
            self.assertIn("Fan 2: 3100 RPM", plot._point_tooltip(plot._rows()[0], 0, 0))
            for index, minimum in ((8, 3), (9, 5)):
                area = plot._bounds()
                point = plot._position(plot._rows()[index], index, 0, plot._maximum(plot._rows()))
                self.drag_point(plot, index, 0, point[0], area.bottom())
                self.assertEqual(tab.entry_edits[index].fan_speed1_edit.text(), str(table1[minimum - 1]))
                self.assertEqual(tab.entry_edits[index].fan_speed2_edit.text(), str(table2[minimum - 1]))
            self.assertEqual(plot._speed(plot._rows()[9], 9, 0), 5)
            controller.on_write_fan_curve_to_hw.assert_not_called()
        finally:
            tab.deleteLater()

    def test_plot_hover_drag_feedback_and_escape_restore_table(self):
        controller, tab, plot = self.make_plot(
            [self.curve_entry()],
            point_count=1,
            temperatures=FanCurveIO.temperature_files,
        )
        try:
            view = tab.entry_edits[0]
            rows = plot._rows()
            start = QPointF(*plot._position(rows[0], 0, 0, plot._maximum(rows)))
            self.app.sendEvent(
                plot,
                QMouseEvent(
                    QEvent.Type.MouseMove,
                    start,
                    Qt.MouseButton.NoButton,
                    Qt.MouseButton.NoButton,
                    Qt.KeyboardModifier.NoModifier,
                ),
            )
            self.assertIn("45–70°C", plot.toolTip())
            self.assertIn("2000 RPM", plot.toolTip())
            self.app.sendEvent(
                plot,
                QMouseEvent(
                    QEvent.Type.MouseButtonPress,
                    start,
                    Qt.MouseButton.LeftButton,
                    Qt.MouseButton.LeftButton,
                    Qt.KeyboardModifier.NoModifier,
                ),
            )
            end = QPointF(plot._bounds().right(), plot._bounds().top())
            self.app.sendEvent(
                plot,
                QMouseEvent(
                    QEvent.Type.MouseMove,
                    end,
                    Qt.MouseButton.LeftButton,
                    Qt.MouseButton.LeftButton,
                    Qt.KeyboardModifier.NoModifier,
                ),
            )
            self.assertNotEqual(view.fan_speed1_edit.text(), "2000")
            self.assertNotEqual(view.cpu_lower_temp_edit.text(), "45")
            plot.grab()  # Selected point badge and current values can render during drag.
            self.app.sendEvent(plot, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier))
            self.assertIsNone(plot._drag)
            self.assertEqual(view.fan_speed1_edit.text(), "2000")
            self.assertEqual(view.cpu_upper_temp_edit.text(), "70")
            self.assertEqual(view.cpu_lower_temp_edit.text(), "45")
            controller.on_write_fan_curve_to_hw.assert_not_called()
        finally:
            tab.deleteLater()

    def test_plot_has_temperature_ticks_and_renders_in_dark_mode(self):
        _, tab, plot = self.make_plot([self.curve_entry()], point_count=1, temperatures=FanCurveIO.temperature_files)
        try:
            self.assertEqual(plot._temperature_range(plot._rows()), (30, 90))
            self.assertEqual(list(plot._x_ticks((30, 90))), list(range(30, 91, 5)))
            palette = plot.palette()
            palette.setColor(QPalette.ColorRole.Window, QColor("#22252a"))
            palette.setColor(QPalette.ColorRole.Base, QColor("#282c33"))
            palette.setColor(QPalette.ColorRole.Text, QColor("#eeeeee"))
            plot.setPalette(palette)
            self.assertFalse(plot.grab().isNull())
        finally:
            tab.deleteLater()

    def test_speed_only_and_hardware_limit_block_temp_and_padding_drag(self):
        controller, tab, plot = self.make_plot([self.curve_entry()], point_count=1, fan2=False)
        try:
            self.assertFalse(plot.temperature_axis)
            self.assertFalse(tab.entry_edits[0].cpu_upper_temp_edit.isEnabled())
            self.assertFalse(tab.entry_edits[1].fan_speed1_edit.isEnabled())
            area = plot._bounds()
            self.drag_point(plot, 0, 0, area.right(), area.top())
            self.assertEqual(tab.entry_edits[0].cpu_upper_temp_edit.text(), "70")
            self.assertEqual(tab.entry_edits[1].fan_speed1_edit.text(), "0")
            controller.on_write_fan_curve_to_hw.assert_not_called()
        finally:
            tab.deleteLater()

    def test_sensor_only_hwmon(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "fan1_input").write_text("2300\n")
            self.check_startup(directory + "/", True, False)

    def test_supported_fancurve(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "pwm1_auto_point1_pwm").write_text("64\n")
            self.check_startup(directory + "/", True, True)

    def test_offline_with_supported_hardware(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "pwm1_auto_point1_pwm").write_text("64\n")
            self.check_startup(directory + "/", False, True)

    def test_no_hwmon(self):
        self.check_startup(None, False, False)

    def test_load_from_preset_with_uninitialized_view(self):
        controller = LegionController(self.app, expect_hwmon=False, use_legion_cli_to_write=True)
        window = MainWindow(controller, QIcon())
        try:
            controller.init(read_from_hw=False)
            # Default view entries have acceleration = 0, deceleration = 0.
            # Loading a preset must not be blocked by validating the uninitialized view.
            with patch.object(controller.model, "load_fancurve_from_preset") as mock_load, patch.object(
                controller, "update_fancurve_gui"
            ) as mock_update:
                controller.view_fancurve.preset_combobox.addItem("performance-ac")
                controller.view_fancurve.preset_combobox.setCurrentText("performance-ac")
                controller.on_load_from_preset()
                mock_load.assert_called_once_with("performance-ac")
                mock_update.assert_called_once()
        finally:
            window.deleteLater()
            self.app.processEvents()

    def test_write_ignores_padding_in_accel_validation(self):
        controller = LegionController(self.app, expect_hwmon=False, use_legion_cli_to_write=True)
        window = MainWindow(controller, QIcon())
        try:
            controller.init(read_from_hw=False)
            # Simulate a preset or hardware read whose trailing entries are
            # all-zero EC padding (issue #493): real points 1-8 with valid
            # acceleration, padding points 9-10 with acceleration = 0.
            for entry_view in controller.view_fancurve.entry_edits[:8]:
                entry_view.fan_speed1_edit.setText("2000")
                entry_view.accel_edit.setText("2")
                entry_view.decel_edit.setText("2")
            with patch.object(controller.model, "write_fancurve_to_hw") as mock_write, patch.object(
                controller.model, "read_fancurve_from_hw"
            ), patch.object(controller, "update_fancurve_gui"):
                controller.on_write_fan_curve_to_hw()
                mock_write.assert_called_once()
                # Padding entries stay in the curve (FanCurveIO.write_fan_curve
                # trims them on write); only validation ignores them.
                self.assertEqual(len(controller.model.fan_curve.entries), 10)
        finally:
            window.deleteLater()
            self.app.processEvents()

    def test_write_rejects_out_of_range_accel_on_real_point(self):
        controller = LegionController(self.app, expect_hwmon=False, use_legion_cli_to_write=True)
        window = MainWindow(controller, QIcon())
        try:
            controller.init(read_from_hw=False)
            # A real (non-padding) point with acceleration outside the
            # controller's 2-5 range must still block the write.
            entry_view = controller.view_fancurve.entry_edits[0]
            entry_view.fan_speed1_edit.setText("2000")
            entry_view.accel_edit.setText("1")
            entry_view.decel_edit.setText("2")
            with patch.object(
                controller.model.fancurve_io, "has_acceleration_curve", return_value=True
            ), patch.object(QMessageBox, "warning"), patch.object(
                controller.model, "write_fancurve_to_hw"
            ) as mock_write:
                controller.on_write_fan_curve_to_hw()
                mock_write.assert_not_called()
        finally:
            window.deleteLater()
            self.app.processEvents()

    def test_write_handles_runtime_error(self):
        controller = LegionController(self.app, expect_hwmon=False, use_legion_cli_to_write=True)
        window = MainWindow(controller, QIcon())
        try:
            controller.init(read_from_hw=False)
            with patch.object(
                controller.model, "write_fancurve_to_hw", side_effect=RuntimeError("legion_cli failed")
            ), patch.object(
                controller.model, "read_fancurve_from_hw"
            ) as mock_read, patch.object(
                controller, "update_fancurve_gui"
            ) as mock_update, patch.object(
                QMessageBox, "warning"
            ) as mock_warning:
                controller.on_write_fan_curve_to_hw()
                mock_warning.assert_called_once()
                mock_read.assert_not_called()
                mock_update.assert_not_called()
        finally:
            window.deleteLater()
            self.app.processEvents()

    def check_native_curve_roundtrip(self, temperature_fields, point_count):
        # Exercise the actual partial sysfs schemas, not mocked read/write calls.
        with tempfile.TemporaryDirectory() as directory:
            hwmon = Path(directory, "hwmon", "hwmon0")
            hwmon.mkdir(parents=True)
            for name in (FanCurveIO.fan1_max, FanCurveIO.fan2_max):
                (hwmon / name).write_text("10000\n")
            (hwmon / FanCurveIO.auto_points_size).write_text(str(point_count))
            Path(directory, legion.FANCURVE_SPEED_UNIT_FILE).write_text("rpm\n")
            patterns = [FanCurveIO.pwm1_fan_speed, FanCurveIO.pwm2_fan_speed]
            patterns.extend(FanCurveIO.temperature_files[name] for name in temperature_fields)
            for point_id in range(1, point_count + 1):
                for pattern in patterns:
                    (hwmon / pattern.format(point_id)).write_text("0\n")

            def write_existing(file_path, value):
                # Unlike normal files, sysfs cannot create unsupported attrs.
                self.assertTrue(Path(file_path).is_file(), file_path)
                self.assertEqual(Path(file_path).parent, hwmon)
                Path(file_path).write_text(str(value))

            with patch.object(legion, "LEGION_SYS_BASEPATH", directory), patch.object(
                FanCurveIO, "hwmon_dir_pattern", str(hwmon)
            ), patch.object(FanCurveIO, "_write_file", side_effect=write_existing), patch.object(
                FileFeature, "_write_file", side_effect=AssertionError("Must not write to real hardware")
            ), patch.object(
                # Direct writes target the fixture, not privileged sysfs.
                legion,
                "is_root_user",
                return_value=True,
            ), patch.object(
                QMessageBox, "warning"
            ) as warning:
                controller = LegionController(self.app, expect_hwmon=True, use_legion_cli_to_write=False)
                window = MainWindow(controller, QIcon())
                try:
                    controller.init(read_from_hw=True)
                    io = controller.model.fancurve_io
                    self.assertFalse(io.uses_fan_levels())
                    self.assertTrue(io.has_fan_2_speed())
                    self.assertTrue(io.has_temperature_curve())
                    self.assertEqual(io.temperature_fields(), temperature_fields)
                    self.assertEqual(io.get_point_count(), point_count)
                    self.assertFalse(io.has_acceleration_curve())
                    self.assertFalse(controller.view_fancurve.minfancurve_check.isEnabled())
                    entry = controller.view_fancurve.entry_edits[0]
                    fields = {
                        "fan_speed1_edit": "4500",
                        "fan_speed2_edit": "4600",
                        "cpu_lower_temp_edit": "50",
                        "cpu_upper_temp_edit": "80",
                        "gpu_lower_temp_edit": "45",
                        "gpu_upper_temp_edit": "75",
                        "ic_lower_temp_edit": "40",
                        "ic_upper_temp_edit": "70",
                    }
                    fields = {
                        name: value
                        for name, value in fields.items()
                        if name.startswith("fan_speed") or name.removesuffix("_edit") in temperature_fields
                    }
                    for name, value in fields.items():
                        field = getattr(entry, name)
                        self.assertTrue(field.isEnabled(), name)
                        field.setText(value)
                    for name in FanCurveIO.temperature_files.keys() - temperature_fields:
                        self.assertFalse(getattr(entry, f"{name}_edit").isEnabled())
                    for unused in controller.view_fancurve.entry_edits[point_count:]:
                        self.assertFalse(unused.fan_speed1_edit.isEnabled())
                    self.assertFalse(entry.accel_edit.isEnabled())
                    self.assertFalse(entry.decel_edit.isEnabled())
                    controller.on_write_fan_curve_to_hw()
                    warning.assert_not_called()
                    for name, value in fields.items():
                        self.assertEqual(float(getattr(entry, name).text()), float(value))
                    # Native EC3 must retain zero RPM, unlike the WMI level path.
                    entry.fan_speed1_edit.setText("0")
                    controller.on_write_fan_curve_to_hw()
                    warning.assert_not_called()
                    self.assertEqual(io.get_fan_1_speed_rpm(1), 0)
                    self.assertEqual(io.get_fan_2_speed_rpm(1), 4600)
                    self.assertEqual(io.get_upper_cpu_temperature(1), 80)
                    for pattern in (FanCurveIO.pwm1_accel, FanCurveIO.pwm1_decel):
                        self.assertFalse((hwmon / pattern.format(1)).exists())
                finally:
                    window.deleteLater()
                    self.app.processEvents()

    def test_ec3_rpm_and_temperature_edit_roundtrip(self):
        self.check_native_curve_roundtrip(set(FanCurveIO.temperature_files), 10)

    def test_ec2_keeps_cpu_gpu_temperatures_and_eight_points(self):
        self.check_native_curve_roundtrip({"cpu_lower_temp", "cpu_upper_temp", "gpu_lower_temp", "gpu_upper_temp"}, 8)

    def test_ec4_keeps_writable_upper_temperatures(self):
        self.check_native_curve_roundtrip({"cpu_upper_temp", "gpu_upper_temp"}, 10)

    def test_unavailable_level_ladder_disables_writes_and_allows_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            hwmon = Path(directory, "hwmon", "hwmon0")
            hwmon.mkdir(parents=True)
            (hwmon / FanCurveIO.pwm1_fan_speed.format(1)).write_text("26\n")
            (hwmon / FanCurveIO.auto_points_size).write_text("1\n")
            Path(directory, legion.FANCURVE_SPEED_UNIT_FILE).write_text("level\n")
            with patch.object(legion, "LEGION_SYS_BASEPATH", directory), patch.object(
                FanCurveIO, "hwmon_dir_pattern", str(hwmon)
            ), patch.object(FileFeature, "_write_file", side_effect=AssertionError("Must not write hardware")):
                controller = LegionController(self.app, expect_hwmon=True, use_legion_cli_to_write=True)
                window = MainWindow(controller, QIcon())
                try:
                    controller.init(read_from_hw=True)
                    self.assertFalse(controller.view_fancurve.write_button.isEnabled())
                    self.assertTrue(controller.view_fancurve.load_button.isEnabled())
                    self.assertIn("ladder is unavailable", controller.view_fancurve.note_label2.text())
                    Path(directory, legion.FAN_LEVEL_RPM_TABLE_FILES[0]).write_text("1700 2000 2500 3000 4000\n")
                    Path(directory, legion.FAN_LEVEL_RPM_TABLE_FILES[1]).write_text("1800 2100 2600 3100 4100\n")
                    controller.on_read_fan_curve_from_hw()
                    self.assertIsNone(controller.fancurve_error)
                    self.assertTrue(controller.view_fancurve.write_button.isEnabled())
                    self.assertEqual(controller.model.fan_curve.entries[0].fan1_speed, 1700)
                    self.assertEqual(controller.model.fan_curve.entries[0].fan2_speed, 1800)
                finally:
                    window.deleteLater()
                    self.app.processEvents()

    def test_tray_preset_failure_is_reported_without_escaping_callback(self):
        model = Mock()
        controller = PresetTrayController(model, [])
        for error in (ValueError("RPM ladder unavailable"), FileNotFoundError("missing preset")):
            with self.subTest(error=type(error).__name__), patch.object(
                model, "fancurve_write_preset_to_hw", side_effect=error
            ) as write, patch.object(QMessageBox, "warning") as warning, patch("legion_linux.legion_gui.log_error"):
                controller.on_action_click("balanced-ac")
                write.assert_called_once_with("balanced-ac")
                warning.assert_called_once()
                self.assertIn(str(error), warning.call_args[0][2])

    def test_write_allows_zero_accel_when_acceleration_curve_unsupported(self):
        controller = LegionController(self.app, expect_hwmon=False, use_legion_cli_to_write=True)
        window = MainWindow(controller, QIcon())
        try:
            controller.init(read_from_hw=False)
            # On models without acceleration curves (wmi_fancurve_speed_only),
            # accel/decel are 0 and disabled in the UI. Writing a real point
            # with accel=0 must not be blocked by validation.
            entry_view = controller.view_fancurve.entry_edits[0]
            entry_view.fan_speed1_edit.setText("2000")
            entry_view.accel_edit.setText("0")
            entry_view.decel_edit.setText("0")
            with patch.object(
                controller.model.fancurve_io, "has_acceleration_curve", return_value=False
            ), patch.object(
                controller.model, "write_fancurve_to_hw"
            ) as mock_write, patch.object(
                controller.model, "read_fancurve_from_hw"
            ), patch.object(
                controller, "update_fancurve_gui"
            ):
                controller.on_write_fan_curve_to_hw()
                mock_write.assert_called_once()
        finally:
            window.deleteLater()
            self.app.processEvents()
