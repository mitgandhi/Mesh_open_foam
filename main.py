"""Command line entry point for the STEP → INP converter."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if SRC_DIR.exists():  # pragma: no branch - deterministic path setup
    sys.path.insert(0, str(SRC_DIR))

from mesh_converter.converter import ConversionSummary, InputFileError, StepParseError, convert_step_to_inp


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert STEP geometry to ABAQUS INP meshes")
    parser.add_argument("input", type=Path, help="Path to the .stp or .step file")
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        help="Destination .inp file. Defaults to the input stem with .inp extension.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = args.output or args.input.with_suffix(".inp")

    try:
        summary: ConversionSummary = convert_step_to_inp(args.input, output)
    except (InputFileError, StepParseError) as exc:
        raise SystemExit(str(exc))

    print("Conversion finished")
    print(f"Nodes: {summary.node_count}")
    print(f"Elements: {summary.element_count}")
    print(f"Ignored duplicates: {summary.ignored_points}")
    print(f"Output written to: {output}")


if __name__ == "__main__":
    main()
