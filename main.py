"""Command line entry point for the STEP → INP converter."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, Optional


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if SRC_DIR.exists():  # pragma: no branch - deterministic path setup
    sys.path.insert(0, str(SRC_DIR))

from mesh_converter.converter import (
    ConversionSummary,
    InputFileError,
    InpParseError,
    StepParseError,
    StretchSummary,
    convert_step_to_inp,
    stretch_inp_geometry,
)


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert STEP geometry to ABAQUS INP meshes or stretch existing INP files"
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to the .stp/.step source file or an existing .inp file",
    )
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        help=(
            "Destination .inp file. Defaults to <input>.inp for STEP sources or "
            "<input>_stretched.inp for INP sources."
        ),
    )
    parser.add_argument(
        "--extend-x",
        type=float,
        default=0.0,
        help="Additional length to add along the X direction when stretching INP files.",
    )
    parser.add_argument(
        "--extend-y",
        type=float,
        default=0.0,
        help="Additional length to add along the Y direction when stretching INP files.",
    )
    parser.add_argument(
        "--extend-z",
        type=float,
        default=0.0,
        help="Additional length to add along the Z direction when stretching INP files.",
    )
    return parser.parse_args(argv)


def _interactive_mode() -> None:
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, simpledialog
    except Exception as exc:  # pragma: no cover - GUI fallback only
        raise SystemExit(
            "Interactive mode requires tkinter to be available.\n"
            f"Encountered error: {exc}"
        )

    root = tk.Tk()
    root.withdraw()

    input_path = filedialog.askopenfilename(
        title="Select STEP or INP file",
        filetypes=(
            ("STEP files", "*.stp *.step"),
            ("INP files", "*.inp"),
            ("All files", "*.*"),
        ),
    )

    if not input_path:
        messagebox.showinfo("Mesh Converter", "No input file selected. Exiting.")
        root.destroy()
        return

    input_path = Path(input_path)
    input_suffix = input_path.suffix.lower()

    try:
        if input_suffix in {".stp", ".step"}:
            output_path = filedialog.asksaveasfilename(
                title="Save INP file as",
                defaultextension=".inp",
                initialfile=f"{input_path.stem}.inp",
                filetypes=(("INP files", "*.inp"), ("All files", "*.*")),
            )

            if not output_path:
                messagebox.showinfo("Mesh Converter", "No output file selected. Exiting.")
                root.destroy()
                return

            output = Path(output_path)
            summary: ConversionSummary = convert_step_to_inp(input_path, output)

            message = (
                "Conversion finished\n"
                f"Nodes: {summary.node_count}\n"
                f"Elements: {summary.element_count}\n"
                f"Ignored duplicates: {summary.ignored_points}\n"
                f"Output written to: {output}"
            )
            messagebox.showinfo("Mesh Converter", message)
        elif input_suffix == ".inp":
            output_path = filedialog.asksaveasfilename(
                title="Save stretched INP file as",
                defaultextension=".inp",
                initialfile=f"{input_path.stem}_stretched.inp",
                filetypes=(("INP files", "*.inp"), ("All files", "*.*")),
            )

            if not output_path:
                messagebox.showinfo("Mesh Converter", "No output file selected. Exiting.")
                root.destroy()
                return

            extend_x = simpledialog.askfloat(
                "Extend X",
                "Additional length along X direction",
                initialvalue=0.0,
            )
            extend_y = simpledialog.askfloat(
                "Extend Y",
                "Additional length along Y direction",
                initialvalue=0.0,
            )
            extend_z = simpledialog.askfloat(
                "Extend Z",
                "Additional length along Z direction",
                initialvalue=0.0,
            )

            if extend_x is None or extend_y is None or extend_z is None:
                messagebox.showinfo("Mesh Converter", "Stretch values not provided. Exiting.")
                root.destroy()
                return

            output = Path(output_path)
            stretch_summary: StretchSummary = stretch_inp_geometry(
                input_path,
                output,
                extend_x=extend_x,
                extend_y=extend_y,
                extend_z=extend_z,
            )

            ox, oy, oz = stretch_summary.original_lengths
            nx, ny, nz = stretch_summary.new_lengths

            lines = [
                "Stretching finished",
                f"Nodes processed: {stretch_summary.node_count}",
            ]
            if stretch_summary.entity_set:
                lines.append(f"Entity set stretched: {stretch_summary.entity_set}")
            lines.extend(
                [
                    "Original extents: "
                    f"X={ox:.6f}, Y={oy:.6f}, Z={oz:.6f}",
                    "Updated extents: "
                    f"X={nx:.6f}, Y={ny:.6f}, Z={nz:.6f}",
                    f"Output written to: {output}",
                ]
            )

            messagebox.showinfo("Mesh Converter", "\n".join(lines))
        else:
            raise InputFileError("Input file must have a .stp, .step or .inp extension")
    except (InputFileError, StepParseError, InpParseError) as exc:
        messagebox.showerror("Mesh Converter", str(exc))
    finally:
        root.destroy()


def main() -> None:
    if len(sys.argv) == 1:
        _interactive_mode()
        return

    args = parse_args()
    input_suffix = args.input.suffix.lower()
    output = args.output

    extends = (args.extend_x, args.extend_y, args.extend_z)

    if input_suffix in {".stp", ".step"}:
        if any(abs(value) > 0.0 for value in extends):
            raise SystemExit(
                "Axis extensions can only be used when providing an INP file as input."
            )

        output = output or args.input.with_suffix(".inp")

        try:
            summary: ConversionSummary = convert_step_to_inp(args.input, output)
        except (InputFileError, StepParseError) as exc:
            raise SystemExit(str(exc))

        print("Conversion finished")
        print(f"Nodes: {summary.node_count}")
        print(f"Elements: {summary.element_count}")
        print(f"Ignored duplicates: {summary.ignored_points}")
        print(f"Output written to: {output}")
        return

    if input_suffix == ".inp":
        output = output or args.input.with_name(f"{args.input.stem}_stretched.inp")

        try:
            stretch_summary: StretchSummary = stretch_inp_geometry(
                args.input,
                output,
                extend_x=args.extend_x,
                extend_y=args.extend_y,
                extend_z=args.extend_z,
            )
        except (InputFileError, InpParseError) as exc:
            raise SystemExit(str(exc))

        print("Stretching finished")
        print(f"Nodes processed: {stretch_summary.node_count}")
        if stretch_summary.entity_set:
            print(f"Entity set stretched: {stretch_summary.entity_set}")
        ox, oy, oz = stretch_summary.original_lengths
        nx, ny, nz = stretch_summary.new_lengths
        print(
            "Original extents: "
            f"X={ox:.6f}, Y={oy:.6f}, Z={oz:.6f}"
        )
        print(
            "Updated extents: "
            f"X={nx:.6f}, Y={ny:.6f}, Z={nz:.6f}"
        )
        print(f"Output written to: {output}")
        return

    raise SystemExit("Input file must have a .stp, .step or .inp extension")


if __name__ == "__main__":
    main()
