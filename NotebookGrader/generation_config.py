"""Validated, working-directory-independent notebook-generation configuration."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


SUPPORTED_ASSIGNMENTS = (1, 2, 3, 4)
PRIVATE_NOTEBOOK_TYPES = (
    "problem",
    "problem_TEST",
    "solution_TEST",
    "problem_solution",
)

REQUIRED_KEYS = (
    "master_notebooks",
    "notebook_file_extension",
    "notebook_folder",
    "target_notebook_folder",
    "target_assignment_master_folder",
    "target_notebook_book_folder",
    "assignments",
    "CourseID",
    "CourseName",
    "CourseInstance",
)


class GenerationConfigError(ValueError):
    """Raised when notebook-generation configuration is unsafe or incomplete."""


def _path_from_config(value: Any, *, key: str, base: Path) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise GenerationConfigError(f"{key} must be a non-empty path string")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve(strict=False)


def _path_from_override(value: str | Path | None, *, fallback: Path) -> Path:
    if value is None:
        return fallback
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve(strict=False)


def _validate_release_list(value: Any) -> tuple[int, ...]:
    if not isinstance(value, list):
        raise GenerationConfigError("assignments must be a JSON list")
    if any(isinstance(number, bool) or not isinstance(number, int) for number in value):
        raise GenerationConfigError("assignments must contain only integer assignment numbers")
    if value != sorted(value):
        raise GenerationConfigError("assignments must be sorted")
    if len(value) != len(set(value)):
        raise GenerationConfigError("assignments must not contain duplicates")
    if any(number not in SUPPORTED_ASSIGNMENTS for number in value):
        raise GenerationConfigError("assignments must be a subset of [1, 2, 3, 4]")
    expected = list(range(1, max(value) + 1)) if value else []
    if value != expected:
        raise GenerationConfigError(
            "assignments must be cumulative: [], [1], [1, 2], [1, 2, 3], or [1, 2, 3, 4]"
        )
    return tuple(value)


def _normalise_master_names(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise GenerationConfigError("master_notebooks must be a non-empty JSON list")

    names: list[str] = []
    for raw_name in value:
        if not isinstance(raw_name, str) or not raw_name.strip():
            raise GenerationConfigError("every master notebook name must be a non-empty string")
        candidate = Path(raw_name)
        if candidate.name != raw_name or raw_name in {".", ".."}:
            raise GenerationConfigError(
                f"master notebook names must be filenames, not paths: {raw_name!r}"
            )
        if candidate.suffix not in {"", ".ipynb"}:
            raise GenerationConfigError(
                f"master notebook must have no suffix or the .ipynb suffix: {raw_name!r}"
            )
        names.append(candidate.stem if candidate.suffix else raw_name)

    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise GenerationConfigError(
            "master notebook names must be unique: " + ", ".join(duplicates)
        )
    return tuple(names)


@dataclass(frozen=True)
class GenerationConfig:
    """Resolved configuration safe to pass to the production parser."""

    config_path: Path
    source_dir: Path
    student_output_dir: Path
    assignment_output_dir: Path
    book_output_dir: Path
    master_names: tuple[str, ...]
    released_assignments: tuple[int, ...]
    course_details: Mapping[str, Any]

    @property
    def master_paths(self) -> tuple[Path, ...]:
        return tuple(self.source_dir / f"{name}.ipynb" for name in self.master_names)

    @property
    def student_outputs(self) -> tuple[Path, ...]:
        return tuple(self.student_output_dir / f"{name}.ipynb" for name in self.master_names)

    @property
    def assignment_outputs(self) -> tuple[Path, ...]:
        return tuple(
            self.assignment_output_dir / f"Assignment_{number}_{notebook_type}.ipynb"
            for number in self.released_assignments
            for notebook_type in PRIVATE_NOTEBOOK_TYPES
        )

    def mutable_course_details(self) -> dict[str, Any]:
        """Return an isolated mapping for ``IDSCourseDetails``."""

        return dict(self.course_details)


def load_generation_config(
    config_path: str | Path,
    *,
    source_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    assignment_output_dir: str | Path | None = None,
) -> GenerationConfig:
    """Load, resolve, and validate generation configuration before notebook parsing.

    Paths stored in JSON are resolved relative to the JSON file. Explicit CLI
    overrides are resolved relative to the caller's current working directory.
    """

    path = Path(config_path).expanduser().resolve(strict=False)
    if not path.is_file():
        raise GenerationConfigError(f"configuration file does not exist: {path}")
    try:
        with path.open(encoding="utf-8") as handle:
            raw = json.load(handle)
    except json.JSONDecodeError as error:
        raise GenerationConfigError(
            f"configuration is not valid JSON at line {error.lineno}, column {error.colno}"
        ) from error
    if not isinstance(raw, dict):
        raise GenerationConfigError("configuration root must be a JSON object")

    missing = [key for key in REQUIRED_KEYS if key not in raw]
    if missing:
        raise GenerationConfigError("configuration is missing required keys: " + ", ".join(missing))

    extension = raw["notebook_file_extension"]
    if extension not in {"ipynb", ".ipynb"}:
        raise GenerationConfigError(
            "the Jupyter generator requires notebook_file_extension to be 'ipynb'"
        )

    for key in ("CourseID", "CourseName", "CourseInstance"):
        if not isinstance(raw[key], str) or not raw[key].strip():
            raise GenerationConfigError(f"{key} must be a non-empty string")

    master_names = _normalise_master_names(raw["master_notebooks"])
    releases = _validate_release_list(raw["assignments"])
    base = path.parent
    configured_source = _path_from_config(raw["notebook_folder"], key="notebook_folder", base=base)
    configured_student = _path_from_config(
        raw["target_notebook_folder"], key="target_notebook_folder", base=base
    )
    configured_assignment = _path_from_config(
        raw["target_assignment_master_folder"],
        key="target_assignment_master_folder",
        base=base,
    )
    book_output = _path_from_config(
        raw["target_notebook_book_folder"], key="target_notebook_book_folder", base=base
    )

    resolved_source = _path_from_override(source_dir, fallback=configured_source)
    resolved_student = _path_from_override(output_dir, fallback=configured_student)
    resolved_assignment = _path_from_override(
        assignment_output_dir, fallback=configured_assignment
    )

    if not resolved_source.is_dir():
        raise GenerationConfigError(f"notebook source directory does not exist: {resolved_source}")
    if resolved_source == resolved_student or resolved_source in resolved_student.parents:
        raise GenerationConfigError(
            "student output directory must be outside the source directory"
        )
    if resolved_source == resolved_assignment or resolved_source in resolved_assignment.parents:
        raise GenerationConfigError(
            "assignment output directory must be outside the source directory"
        )
    if resolved_student == resolved_assignment:
        raise GenerationConfigError(
            "student and private assignment output directories must be different"
        )

    master_paths = tuple(resolved_source / f"{name}.ipynb" for name in master_names)
    missing_masters = [str(master) for master in master_paths if not master.is_file()]
    if missing_masters:
        raise GenerationConfigError(
            "master notebook files do not exist: " + ", ".join(missing_masters)
        )
    for number in releases:
        expected_name = f"Assignment_{number}"
        if expected_name not in master_names:
            raise GenerationConfigError(
                f"released assignment {number} has no {expected_name}.ipynb master"
            )

    details = dict(raw)
    details.update(
        master_notebooks=list(master_names),
        notebook_file_extension="ipynb",
        notebook_folder=str(resolved_source),
        target_notebook_folder=str(resolved_student),
        target_assignment_master_folder=str(resolved_assignment),
        target_notebook_book_folder=str(book_output),
        assignments=list(releases),
    )

    return GenerationConfig(
        config_path=path,
        source_dir=resolved_source,
        student_output_dir=resolved_student,
        assignment_output_dir=resolved_assignment,
        book_output_dir=book_output,
        master_names=master_names,
        released_assignments=releases,
        course_details=details,
    )


def validate_release_list(value: Sequence[int]) -> tuple[int, ...]:
    """Public helper used by the grader-manifest preflight."""

    return _validate_release_list(value)
