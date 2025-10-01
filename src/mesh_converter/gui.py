"""PyQt5 GUI for converting STEP files into INP meshes."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QWidget,
)

from .converter import ConversionSummary, InputFileError, StepParseError, convert_step_to_inp


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

        layout = QGridLayout()
        central_widget.setLayout(layout)

        # Input file selection row
        input_label = QLabel("STEP file:")
        self.input_path_edit = QLineEdit()
        self.input_path_edit.setPlaceholderText("Select a .stp or .step file")
        browse_input_button = QPushButton("Browse…")
        browse_input_button.clicked.connect(self._choose_input_file)

        layout.addWidget(input_label, 0, 0)
        layout.addWidget(self.input_path_edit, 0, 1)
        layout.addWidget(browse_input_button, 0, 2)

        # Output file selection row
        output_label = QLabel("Output .inp:")
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("Select destination for the .inp file")
        browse_output_button = QPushButton("Browse…")
        browse_output_button.clicked.connect(self._choose_output_file)

        layout.addWidget(output_label, 1, 0)
        layout.addWidget(self.output_path_edit, 1, 1)
        layout.addWidget(browse_output_button, 1, 2)

        # Convert button and status output
        button_layout = QHBoxLayout()
        self.convert_button = QPushButton("Convert")
        self.convert_button.clicked.connect(self._convert)
        button_layout.addWidget(self.convert_button)
        button_layout.addStretch()

        layout.addLayout(button_layout, 2, 0, 1, 3)

        self.status_box = QTextEdit()
        self.status_box.setReadOnly(True)
        self.status_box.setPlaceholderText("Conversion logs will appear here…")
        layout.addWidget(self.status_box, 3, 0, 1, 3)

        layout.setColumnStretch(1, 1)

    # Slots -----------------------------------------------------------------

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
