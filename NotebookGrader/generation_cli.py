"""Shared command-line implementation for Jupyter notebook generation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Mapping, Sequence

import nbformat

from .AssignmentNotebook.IDSAssignmentNotebook import IDSCourse, IDSCourseDetails
from .generation_config import (
    GenerationConfig,
    load_generation_config,
)


DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "configNotebooks.json"


def build_parser(*, private_variants: bool) -> argparse.ArgumentParser:
    artifact = "private assignment variants" if private_variants else "student notebooks"
    parser = argparse.ArgumentParser(
        description=f"Generate or validate {artifact} with the production GenJSON parser.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--source-dir",
        type=Path,
        help="override notebook_folder from the configuration",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="override target_notebook_folder from the configuration",
    )
    parser.add_argument(
        "--assignment-output-dir",
        type=Path,
        help="override target_assignment_master_folder from the configuration",
    )
    if private_variants:
        parser.add_argument(
            "--assignment",
            type=int,
            action="append",
            dest="assignments",
            metavar="NUMBER",
            help=(
                "generate this assignment even when it is not in the configuration's "
                "assignments release list; may be repeated"
            ),
        )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_only",
        help="print resolved inputs and outputs without writing",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="parse and validate the selected artifacts without writing",
    )
    parser.add_argument("--verbose", action="store_true")
    return parser


def _print_resolution(config: GenerationConfig) -> None:
    print(f"config: {config.config_path}")
    print(f"source-dir: {config.source_dir}")
    print(f"student-output-dir: {config.student_output_dir}")
    print(f"assignment-output-dir: {config.assignment_output_dir}")
    releases = ",".join(str(number) for number in config.released_assignments)
    print(f"release-list: [{releases}]")
    for source in config.master_paths:
        print(f"input: {source}")
    for output in config.student_outputs:
        print(f"student-output: {output}")
    for output in config.assignment_outputs:
        print(f"private-output: {output}")


def _validated_notebooks(
    config: GenerationConfig, *, private_variants: bool, verbose: bool
) -> Mapping[str, nbformat.NotebookNode]:
    details = IDSCourseDetails(config.mutable_course_details())
    course = IDSCourse(courseDetails=details, verbose=verbose)
    notebooks = (
        course.assignment_notebooks()
        if private_variants
        else course.student_notebooks()
    )
    for filename, notebook in notebooks.items():
        try:
            nbformat.validate(notebook)
        except Exception as error:
            raise ValueError(f"generated notebook is invalid: {filename}: {error}") from error
    return notebooks


def _canonicalize_cell_ids(notebook: nbformat.NotebookNode) -> None:
    """Assign deterministic, unique nbformat cell IDs for final serialization."""

    used: set[str] = set()
    for index, cell in enumerate(notebook.cells):
        semantic_cell = {key: value for key, value in cell.items() if key != "id"}
        semantic_json = json.dumps(
            semantic_cell,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        seed = f"{index}\0{semantic_json}".encode("utf-8")
        nonce = 0
        while True:
            material = seed if nonce == 0 else seed + f"\0{nonce}".encode("ascii")
            candidate = "c" + hashlib.sha256(material).hexdigest()[:31]
            if candidate not in used:
                break
            nonce += 1
        cell["id"] = candidate
        used.add(candidate)


def _write_notebooks(
    notebooks: Mapping[str, nbformat.NotebookNode], destination: Path, *, verbose: bool
) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for filename, notebook in notebooks.items():
        _canonicalize_cell_ids(notebook)
        nbformat.validate(notebook)
        target = destination / filename
        temporary_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=destination,
                prefix=f".{filename}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary_name = handle.name
                nbformat.write(notebook, handle)
            os.replace(temporary_name, target)
            temporary_name = None
        finally:
            if temporary_name is not None:
                Path(temporary_name).unlink(missing_ok=True)
        if verbose:
            print(f"wrote: {target}")


def run(argv: Sequence[str] | None = None, *, private_variants: bool) -> int:
    parser = build_parser(private_variants=private_variants)
    args = parser.parse_args(argv)
    try:
        config = load_generation_config(
            args.config,
            source_dir=args.source_dir,
            output_dir=args.output_dir,
            assignment_output_dir=args.assignment_output_dir,
        )
        if private_variants and args.assignments:
            config = config.select_assignments(args.assignments)
        if args.list_only:
            _print_resolution(config)

        notebooks = None
        if args.check or not args.list_only:
            notebooks = _validated_notebooks(
                config,
                private_variants=private_variants,
                verbose=args.verbose,
            )

        if args.list_only or args.check:
            if args.check:
                kind = "private assignment" if private_variants else "student"
                print(f"Validated {len(notebooks or {})} {kind} notebooks; no files written.")
            return 0

        assert notebooks is not None
        destination = (
            config.assignment_output_dir if private_variants else config.student_output_dir
        )
        _write_notebooks(notebooks, destination, verbose=args.verbose)
        kind = "private assignment" if private_variants else "student"
        print(f"Generated {len(notebooks)} {kind} notebooks in {destination}")
        return 0
    except Exception as error:
        print(f"ERROR {type(error).__name__}: {error}", file=sys.stderr)
        return 2


def student_main(argv: Sequence[str] | None = None) -> int:
    return run(argv, private_variants=False)


def assignment_main(argv: Sequence[str] | None = None) -> int:
    return run(argv, private_variants=True)
