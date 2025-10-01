"""PyQt5 GUI for converting STEP files into INP meshes."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .converter import (
    ConversionSummary,
    InputFileError,
    InpParseError,
    StepParseError,
    StretchSummary,
    convert_step_to_inp,
    list_inp_entity_sets,
    stretch_inp_geometry,
)


class MainWindow(QMainWindow):
    """Main application window that wires together the converter and the UI."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("STEP → INP Mesh Converter")
        self.setMinimumSize(600, 300)
        self._build_ui()

    def _build_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # STEP → INP conversion controls
        convert_group = QGroupBox("Convert STEP file")
        convert_layout = QGridLayout()
        convert_group.setLayout(convert_layout)

        input_label = QLabel("STEP file:")
        self.input_path_edit = QLineEdit()
        self.input_path_edit.setPlaceholderText("Select a .stp or .step file")
        browse_input_button = QPushButton("Browse…")
        browse_input_button.clicked.connect(self._choose_input_file)

        convert_layout.addWidget(input_label, 0, 0)
        convert_layout.addWidget(self.input_path_edit, 0, 1)
        convert_layout.addWidget(browse_input_button, 0, 2)

        output_label = QLabel("Output .inp:")
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("Select destination for the .inp file")
        browse_output_button = QPushButton("Browse…")
        browse_output_button.clicked.connect(self._choose_output_file)

        convert_layout.addWidget(output_label, 1, 0)
        convert_layout.addWidget(self.output_path_edit, 1, 1)
        convert_layout.addWidget(browse_output_button, 1, 2)

        convert_button_layout = QHBoxLayout()
        self.convert_button = QPushButton("Convert")
        self.convert_button.clicked.connect(self._convert)
        convert_button_layout.addWidget(self.convert_button)
        convert_button_layout.addStretch()

        convert_layout.addLayout(convert_button_layout, 2, 0, 1, 3)
        convert_layout.setColumnStretch(1, 1)

        main_layout.addWidget(convert_group)

        # INP stretching controls
        stretch_group = QGroupBox("Stretch existing INP file")
        stretch_layout = QGridLayout()
        stretch_group.setLayout(stretch_layout)

        stretch_input_label = QLabel("INP file:")
        self.stretch_input_edit = QLineEdit()
        self.stretch_input_edit.setPlaceholderText("Select an existing .inp file")
        browse_stretch_input = QPushButton("Browse…")
        browse_stretch_input.clicked.connect(self._choose_stretch_input_file)

        stretch_layout.addWidget(stretch_input_label, 0, 0)
        stretch_layout.addWidget(self.stretch_input_edit, 0, 1)
        stretch_layout.addWidget(browse_stretch_input, 0, 2)

        stretch_output_label = QLabel("Output .inp:")
        self.stretch_output_edit = QLineEdit()
        self.stretch_output_edit.setPlaceholderText("Select destination for the stretched .inp file")
        browse_stretch_output = QPushButton("Browse…")
        browse_stretch_output.clicked.connect(self._choose_stretch_output_file)

        stretch_layout.addWidget(stretch_output_label, 1, 0)
        stretch_layout.addWidget(self.stretch_output_edit, 1, 1)
        stretch_layout.addWidget(browse_stretch_output, 1, 2)

        entity_label = QLabel("Entity set:")
        self.entity_set_combo = QComboBox()
        self.entity_set_combo.addItem("All nodes", None)
        self.entity_set_combo.setEnabled(False)

        stretch_layout.addWidget(entity_label, 2, 0)
        stretch_layout.addWidget(self.entity_set_combo, 2, 1, 1, 2)

        extend_label = QLabel("Axis extensions:")
        extends_layout = QHBoxLayout()
        self.extend_x_spin = self._create_extension_spinbox()
        self.extend_y_spin = self._create_extension_spinbox()
        self.extend_z_spin = self._create_extension_spinbox()
        extends_layout.addWidget(QLabel("ΔX"))
        extends_layout.addWidget(self.extend_x_spin)
        extends_layout.addWidget(QLabel("ΔY"))
        extends_layout.addWidget(self.extend_y_spin)
        extends_layout.addWidget(QLabel("ΔZ"))
        extends_layout.addWidget(self.extend_z_spin)
        extends_layout.addStretch()

        stretch_layout.addWidget(extend_label, 3, 0)
        stretch_layout.addLayout(extends_layout, 3, 1, 1, 2)

        stretch_button_layout = QHBoxLayout()
        self.stretch_button = QPushButton("Stretch")
        self.stretch_button.clicked.connect(self._stretch)
        stretch_button_layout.addWidget(self.stretch_button)
        stretch_button_layout.addStretch()

        stretch_layout.addLayout(stretch_button_layout, 4, 0, 1, 3)
        stretch_layout.setColumnStretch(1, 1)

        main_layout.addWidget(stretch_group)

        # Shared status output
        self.status_box = QTextEdit()
        self.status_box.setReadOnly(True)
        self.status_box.setPlaceholderText("Conversion and stretching logs will appear here…")
        main_layout.addWidget(self.status_box)

    # Slots -----------------------------------------------------------------

    def _create_extension_spinbox(self) -> QDoubleSpinBox:
        spin_box = QDoubleSpinBox()
        spin_box.setDecimals(6)
        spin_box.setRange(-1_000_000.0, 1_000_000.0)
        spin_box.setSingleStep(0.1)
        spin_box.setValue(0.0)
        return spin_box

    def _choose_input_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select STEP file",
            "",
            "STEP Files (*.stp *.step)",
        )
        if file_path:
            self.input_path_edit.setText(file_path)

    def _choose_output_file(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select output INP file",
            "",
            "INP Files (*.inp)",
        )
        if file_path:
            if not file_path.lower().endswith(".inp"):
                file_path += ".inp"
            self.output_path_edit.setText(file_path)

    def _choose_stretch_input_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select INP file",
            "",
            "INP Files (*.inp)",
        )
        if file_path:
            self.stretch_input_edit.setText(file_path)
            if not self.stretch_output_edit.text().strip():
                path = Path(file_path)
                self.stretch_output_edit.setText(str(path.with_name(f"{path.stem}_stretched.inp")))
            self._load_entity_sets(Path(file_path))

    def _choose_stretch_output_file(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select output INP file",
            "",
            "INP Files (*.inp)",
        )
        if file_path:
            if not file_path.lower().endswith(".inp"):
                file_path += ".inp"
            self.stretch_output_edit.setText(file_path)

    def _convert(self) -> None:
        input_path = self.input_path_edit.text().strip()
        output_path = self.output_path_edit.text().strip()

        if not input_path:
            self._show_error("Please select a STEP file to convert.")
            return

        if not output_path:
            self._show_error("Please choose a destination for the INP file.")
            return

        try:
            summary = convert_step_to_inp(input_path, output_path)
        except (InputFileError, StepParseError) as exc:
            self._show_error(str(exc))
            return
        except Exception as exc:  # pragma: no cover - defensive guard
            self._show_error(f"Unexpected error: {exc}")
            return

        self._show_summary(summary, Path(output_path))

    def _load_entity_sets(self, input_path: Path) -> None:
        try:
            entity_sets = list_inp_entity_sets(input_path)
        except (InputFileError, InpParseError) as exc:
            self._show_error(str(exc))
            self.entity_set_combo.clear()
            self.entity_set_combo.addItem("All nodes", None)
            self.entity_set_combo.setEnabled(False)
            return
        except Exception as exc:  # pragma: no cover - defensive guard
            self._show_error(f"Unexpected error while reading entity sets: {exc}")
            self.entity_set_combo.clear()
            self.entity_set_combo.addItem("All nodes", None)
            self.entity_set_combo.setEnabled(False)
            return

        self.entity_set_combo.blockSignals(True)
        self.entity_set_combo.clear()
        self.entity_set_combo.addItem("All nodes", None)
        for name in sorted(entity_sets):
            self.entity_set_combo.addItem(name, tuple(entity_sets[name]))
        self.entity_set_combo.setEnabled(True)
        self.entity_set_combo.blockSignals(False)

        message = "Loaded entity sets: " + ", ".join(sorted(entity_sets)) if entity_sets else "No entity sets found"
        self.status_box.append(message)

    def _stretch(self) -> None:
        input_path = self.stretch_input_edit.text().strip()
        output_path = self.stretch_output_edit.text().strip()

        if not input_path:
            self._show_error("Please select an INP file to stretch.")
            return

        if not output_path:
            self._show_error("Please choose a destination for the stretched INP file.")
            return

        entity_data = self.entity_set_combo.currentData()
        entity_name = None
        node_ids = None
        if entity_data:
            entity_name = self.entity_set_combo.currentText()
            node_ids = list(entity_data)

        try:
            summary = stretch_inp_geometry(
                input_path,
                output_path,
                extend_x=self.extend_x_spin.value(),
                extend_y=self.extend_y_spin.value(),
                extend_z=self.extend_z_spin.value(),
                target_node_ids=node_ids,
                entity_name=entity_name,
            )
        except (InputFileError, InpParseError) as exc:
            self._show_error(str(exc))
            return
        except Exception as exc:  # pragma: no cover - defensive guard
            self._show_error(f"Unexpected error: {exc}")
            return

        self._show_stretch_summary(summary, Path(output_path))

    def _show_summary(self, summary: ConversionSummary, output_path: Path) -> None:
        message = (
            f"Conversion complete!\n"
            f"Nodes: {summary.node_count}\n"
            f"Elements: {summary.element_count}\n"
            f"Ignored duplicates: {summary.ignored_points}\n"
            f"Output saved to: {output_path}"
        )
        self.status_box.append(message)
        QMessageBox.information(self, "Conversion complete", message)

    def _show_stretch_summary(self, summary: StretchSummary, output_path: Path) -> None:
        entity_line = summary.entity_set if summary.entity_set else "All nodes"
        message = (
            f"Stretching complete!\n"
            f"Entity: {entity_line}\n"
            f"Nodes adjusted: {summary.node_count}\n"
            f"Original extents: X={summary.original_lengths[0]:.6f}, "
            f"Y={summary.original_lengths[1]:.6f}, Z={summary.original_lengths[2]:.6f}\n"
            f"Updated extents: X={summary.new_lengths[0]:.6f}, "
            f"Y={summary.new_lengths[1]:.6f}, Z={summary.new_lengths[2]:.6f}\n"
            f"Output saved to: {output_path}"
        )
        self.status_box.append(message)
        QMessageBox.information(self, "Stretch complete", message)

    def _show_error(self, message: str) -> None:
        self.status_box.append(f"Error: {message}")
        QMessageBox.critical(self, "Conversion failed", message)


def run() -> None:
    """Launch the Qt application."""

    app = QApplication(sys.argv)
    app.setApplicationName("STEP → INP Mesh Converter")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    run()
