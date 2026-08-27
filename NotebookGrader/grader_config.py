"""Secret-safe local configuration and installed-master preflights for grading."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import stat
import subprocess
from typing import Any, Mapping
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import nbformat

from .generation_config import GenerationConfigError, validate_release_list


MANIFEST_SCHEMA_VERSION = 1
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
MASTER_NAME_PATTERN = re.compile(r"Assignment_([1-4])_problem_TEST\.ipynb")
DEFAULT_TIMEZONE = "Europe/Stockholm"
DEFAULT_POLL_INTERVAL_SECONDS = 12 * 60 * 60


class GraderConfigError(ValueError):
    """Raised when local grading configuration cannot be used safely."""


@dataclass(frozen=True)
class GraderAssignment:
    number: int
    name: str
    studium_id: int | None
    master_path: Path
    start_date: date
    end_date: date
    master_sha256: str
    source_sha256: str

    def window(self, timezone: ZoneInfo) -> tuple[datetime, datetime]:
        return (
            datetime.combine(self.start_date, time(hour=0, minute=1), tzinfo=timezone),
            datetime.combine(self.end_date, time(hour=23, minute=59), tzinfo=timezone),
        )


@dataclass(frozen=True)
class GraderConfiguration:
    path: Path
    api_url: str
    api_key: str = field(repr=False)
    course_id: int = 0
    assignments: tuple[GraderAssignment, ...] = ()
    released_assignments: tuple[int, ...] = ()
    timezone: ZoneInfo = field(default_factory=lambda: ZoneInfo(DEFAULT_TIMEZONE))
    poll_interval_seconds: int = DEFAULT_POLL_INTERVAL_SECONDS
    docker_image: str = "itds-autograde:latest"
    source_dir: Path = Path("courseLink/master/jp")
    data_dir: Path = Path("courseLink/master/jp/data")
    utils_file: Path = Path("Utils.py")
    manifest_path: Path = Path("grader-manifest.json")
    permission_warning: str | None = None


def _resolve_path(value: Any, *, key: str, base: Path) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise GraderConfigError(f"{key} must be a non-empty path string")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve(strict=False)


def _read_json(path: Path, *, description: str) -> Mapping[str, Any]:
    if not path.is_file():
        raise GraderConfigError(f"{description} does not exist: {path}")
    try:
        with path.open(encoding="utf-8") as handle:
            value = json.load(handle)
    except json.JSONDecodeError as error:
        raise GraderConfigError(
            f"{description} is not valid JSON at line {error.lineno}, column {error.colno}"
        ) from error
    if not isinstance(value, dict):
        raise GraderConfigError(f"{description} root must be a JSON object")
    return value


def ensure_local_config_is_private(path: Path) -> str | None:
    """Require a local grader config to be untracked and covered by Git ignore rules."""

    repository = subprocess.run(
        ["git", "-C", str(path.parent), "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if repository.returncode != 0:
        raise GraderConfigError(
            "grader configuration must be inside a Git worktree so ignore status can be verified"
        )
    root = Path(repository.stdout.strip()).resolve()
    try:
        relative = path.resolve().relative_to(root)
    except ValueError as error:
        raise GraderConfigError("grader configuration is outside its resolved Git worktree") from error

    tracked = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--error-unmatch", "--", str(relative)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if tracked.returncode == 0:
        raise GraderConfigError("grader configuration is tracked by Git; remove it from the index")
    ignored = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "--quiet", "--", str(relative)],
        check=False,
    )
    if ignored.returncode != 0:
        raise GraderConfigError("grader configuration is not covered by a Git ignore rule")

    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except OSError:
        return None
    if mode & 0o077:
        return f"grader configuration permissions are {mode:o}; consider: chmod 600 {path}"
    return None


def _validate_api_url(value: Any) -> str:
    if not isinstance(value, str):
        raise GraderConfigError("API_URL must be an HTTPS URL")
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise GraderConfigError("API_URL must be a credential-free HTTPS origin")
    return value.rstrip("/")


def _validate_token(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GraderConfigError("API_KEY must be a non-empty local token")
    lowered = value.lower()
    if "xxxx" in lowered or "<canvas" in lowered or "replace" in lowered:
        raise GraderConfigError("API_KEY still contains a template placeholder")
    return value


def _parse_date(value: Any, *, key: str) -> date:
    if not isinstance(value, str):
        raise GraderConfigError(f"{key} must use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise GraderConfigError(f"{key} must use YYYY-MM-DD") from error


def _parse_assignment(raw: Any, *, base: Path) -> GraderAssignment:
    if not isinstance(raw, dict):
        raise GraderConfigError("every Assignments entry must be a JSON object")
    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        raise GraderConfigError("every assignment must have a non-empty name")
    master = _resolve_path(raw.get("master_filename"), key="master_filename", base=base)
    match = MASTER_NAME_PATTERN.fullmatch(master.name)
    if match is None:
        raise GraderConfigError(
            f"assignment master must be named Assignment_N_problem_TEST.ipynb: {master.name}"
        )
    inferred_number = int(match.group(1))
    number = raw.get("number", inferred_number)
    if isinstance(number, bool) or not isinstance(number, int) or number != inferred_number:
        raise GraderConfigError(
            f"assignment number must match the problem_TEST filename: {master.name}"
        )
    studium_id = raw.get("studium_id")
    if studium_id is not None and (
        isinstance(studium_id, bool) or not isinstance(studium_id, int) or studium_id < 0
    ):
        raise GraderConfigError(f"studium_id for assignment {number} must be a nonnegative integer")
    start = _parse_date(raw.get("start_date"), key=f"assignment {number} start_date")
    end = _parse_date(raw.get("end_date"), key=f"assignment {number} end_date")
    if end < start:
        raise GraderConfigError(f"assignment {number} end_date precedes start_date")
    return GraderAssignment(
        number=number,
        name=name.strip(),
        studium_id=studium_id,
        master_path=master,
        start_date=start,
        end_date=end,
        master_sha256="",
        source_sha256="",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_master_notebook(path: Path, number: int) -> None:
    if not path.is_file():
        raise GraderConfigError(f"installed problem_TEST master does not exist: {path}")
    try:
        notebook = nbformat.read(path, as_version=4)
        nbformat.validate(notebook)
    except Exception as error:
        raise GraderConfigError(
            f"installed problem_TEST master is not a valid notebook: {path.name}"
        ) from error
    metadata_number = notebook.metadata.get("lx_assignment_number")
    if str(metadata_number) != str(number):
        raise GraderConfigError(
            f"installed master assignment metadata does not match assignment {number}"
        )
    cells_by_problem: dict[str, list[str]] = {}
    for cell in notebook.cells:
        cell_type = cell.metadata.get("lx_problem_cell_type")
        problem = cell.metadata.get("lx_problem_number")
        if cell_type is not None and problem is not None:
            cells_by_problem.setdefault(str(problem), []).append(str(cell_type))
    if not cells_by_problem:
        raise GraderConfigError(f"installed master has no scored problems: {path.name}")
    for problem, cell_types in cells_by_problem.items():
        if "PROBLEM" not in cell_types or cell_types.count("TEST") != 1:
            raise GraderConfigError(
                f"installed master problem {problem} must contain PROBLEM and exactly one TEST cell"
            )
        if "SOLUTION" in cell_types:
            raise GraderConfigError(
                f"installed problem_TEST master unexpectedly contains a SOLUTION cell: {path.name}"
            )


def _load_manifest(path: Path) -> tuple[tuple[int, ...], Mapping[str, Any]]:
    manifest = _read_json(path, description="grader manifest")
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise GraderConfigError(
            f"grader manifest schema_version must be {MANIFEST_SCHEMA_VERSION}"
        )
    try:
        releases = validate_release_list(manifest.get("release_assignments"))
    except GenerationConfigError as error:
        raise GraderConfigError(f"invalid grader manifest release list: {error}") from error
    entries = manifest.get("assignments")
    if not isinstance(entries, dict):
        raise GraderConfigError("grader manifest assignments must be a JSON object")
    expected_keys = {str(number) for number in releases}
    if set(entries) != expected_keys:
        raise GraderConfigError(
            "grader manifest assignment entries must exactly match release_assignments"
        )
    return releases, entries


def _manifest_values(entry: Any, *, number: int) -> tuple[str, str, str]:
    if not isinstance(entry, dict):
        raise GraderConfigError(f"grader manifest entry {number} must be a JSON object")
    filename = entry.get("problem_TEST")
    expected = f"Assignment_{number}_problem_TEST.ipynb"
    if filename != expected:
        raise GraderConfigError(f"grader manifest entry {number} must name {expected}")
    digest = entry.get("sha256")
    source_digest = entry.get("source_sha256")
    if not isinstance(digest, str) or SHA256_PATTERN.fullmatch(digest) is None:
        raise GraderConfigError(f"grader manifest entry {number} has an invalid sha256")
    if not isinstance(source_digest, str) or SHA256_PATTERN.fullmatch(source_digest) is None:
        raise GraderConfigError(f"grader manifest entry {number} has an invalid source_sha256")
    return filename, digest, source_digest


def validate_runtime(configuration: GraderConfiguration) -> None:
    """Validate the local sandbox runtime without contacting Canvas."""

    if not configuration.data_dir.is_dir():
        raise GraderConfigError(f"grader data directory does not exist: {configuration.data_dir}")
    if not configuration.utils_file.is_file():
        raise GraderConfigError(f"grader Utils.py does not exist: {configuration.utils_file}")
    if importlib.util.find_spec("epicbox") is None:
        raise GraderConfigError("Epicbox is not installed in the grader environment")
    docker = shutil.which("docker")
    if docker is None:
        raise GraderConfigError("Docker CLI is not installed")
    inspected = subprocess.run(
        [docker, "image", "inspect", configuration.docker_image],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if inspected.returncode != 0:
        raise GraderConfigError(
            f"required Docker image is unavailable: {configuration.docker_image}"
        )


def load_grader_config(
    config_path: str | Path,
    *,
    assignment_number: int | None = None,
    manifest_path: str | Path | None = None,
    check_git: bool = True,
    check_runtime: bool = True,
) -> GraderConfiguration:
    """Validate all local state required before constructing a Canvas client."""

    path = Path(config_path).expanduser().resolve(strict=False)
    if not path.is_file():
        raise GraderConfigError(f"grader configuration does not exist: {path}")
    permission_warning = ensure_local_config_is_private(path) if check_git else None
    raw = _read_json(path, description="grader configuration")
    base = path.parent

    course_id = raw.get("course")
    if isinstance(course_id, bool) or not isinstance(course_id, int) or course_id <= 0:
        raise GraderConfigError("course must be a positive Canvas course ID")
    api_url = _validate_api_url(raw.get("API_URL"))
    api_key = _validate_token(raw.get("API_KEY"))
    assignment_values = raw.get("Assignments")
    if not isinstance(assignment_values, list) or not assignment_values:
        raise GraderConfigError("Assignments must be a non-empty JSON list")
    parsed_assignments = tuple(
        _parse_assignment(value, base=base) for value in assignment_values
    )
    numbers = [assignment.number for assignment in parsed_assignments]
    names = [assignment.name for assignment in parsed_assignments]
    if len(numbers) != len(set(numbers)):
        raise GraderConfigError("Assignments contains duplicate assignment numbers")
    if len(names) != len(set(names)):
        raise GraderConfigError("Assignments contains duplicate Canvas assignment names")

    timezone_name = raw.get("timezone", DEFAULT_TIMEZONE)
    if timezone_name != DEFAULT_TIMEZONE:
        raise GraderConfigError(f"timezone must be {DEFAULT_TIMEZONE}")
    try:
        timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as error:
        raise GraderConfigError(f"timezone data is unavailable for {timezone_name}") from error
    poll_interval = raw.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS)
    if (
        isinstance(poll_interval, bool)
        or not isinstance(poll_interval, int)
        or poll_interval < 60
    ):
        raise GraderConfigError("poll_interval_seconds must be an integer of at least 60")
    docker_image = raw.get("docker_image", "itds-autograde:latest")
    if not isinstance(docker_image, str) or not docker_image.strip():
        raise GraderConfigError("docker_image must be a non-empty string")
    source_dir = _resolve_path(
        raw.get("source_dir", "courseLink/master/jp"), key="source_dir", base=base
    )
    data_dir = _resolve_path(
        raw.get("data_dir", "courseLink/master/jp/data"), key="data_dir", base=base
    )
    utils_file = _resolve_path(
        raw.get("utils_file", "courseLink/master/jp/Utils.py"),
        key="utils_file",
        base=base,
    )

    if manifest_path is None:
        manifest_value = raw.get("grader_manifest")
        if manifest_value is None:
            manifest = parsed_assignments[0].master_path.parent / "grader-manifest.json"
        else:
            manifest = _resolve_path(manifest_value, key="grader_manifest", base=base)
    else:
        candidate = Path(manifest_path).expanduser()
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate
        manifest = candidate.resolve(strict=False)

    releases, manifest_entries = _load_manifest(manifest)
    configured_by_number = {assignment.number: assignment for assignment in parsed_assignments}
    missing_config = [number for number in releases if number not in configured_by_number]
    if missing_config:
        raise GraderConfigError(
            "released assignments are missing grader configuration: "
            + ", ".join(str(number) for number in missing_config)
        )
    if assignment_number is not None and assignment_number not in releases:
        raise GraderConfigError(
            f"assignment {assignment_number} is not released in the installed grader manifest"
        )
    selected_numbers = (assignment_number,) if assignment_number is not None else releases
    selected: list[GraderAssignment] = []
    for number in selected_numbers:
        assignment = configured_by_number[number]
        filename, expected_digest, source_digest = _manifest_values(
            manifest_entries[str(number)], number=number
        )
        installed_path = (manifest.parent / filename).resolve()
        if installed_path != assignment.master_path.resolve():
            raise GraderConfigError(
                f"assignment {number} config and grader manifest identify different masters"
            )
        _validate_master_notebook(installed_path, number)
        actual_digest = _sha256(installed_path)
        if actual_digest != expected_digest:
            raise GraderConfigError(
                f"installed problem_TEST master hash does not match the grader manifest: {filename}"
            )
        source_path = source_dir / f"Assignment_{number}.ipynb"
        if not source_path.is_file():
            raise GraderConfigError(
                f"canonical assignment source does not exist: {source_path}"
            )
        if _sha256(source_path) != source_digest:
            raise GraderConfigError(
                f"canonical assignment source hash does not match the grader manifest: {source_path.name}"
            )
        selected.append(
            GraderAssignment(
                number=assignment.number,
                name=assignment.name,
                studium_id=assignment.studium_id,
                master_path=installed_path,
                start_date=assignment.start_date,
                end_date=assignment.end_date,
                master_sha256=actual_digest,
                source_sha256=source_digest,
            )
        )

    configuration = GraderConfiguration(
        path=path,
        api_url=api_url,
        api_key=api_key,
        course_id=course_id,
        assignments=tuple(selected),
        released_assignments=releases,
        timezone=timezone,
        poll_interval_seconds=poll_interval,
        docker_image=docker_image.strip(),
        source_dir=source_dir,
        data_dir=data_dir,
        utils_file=utils_file,
        manifest_path=manifest,
        permission_warning=permission_warning,
    )
    if check_runtime:
        validate_runtime(configuration)
    return configuration


def redact_error(error: BaseException, *, secrets: tuple[str, ...] = ()) -> str:
    """Return a single-line error message with tokens and token query values removed."""

    message = str(error).replace("\n", " ").replace("\r", " ")
    for secret in secrets:
        if secret:
            message = message.replace(secret, "<redacted>")
    message = re.sub(r"(?i)(access_token=)[^&\s]+", r"\1<redacted>", message)
    message = re.sub(r"(?i)(api[_-]?key[=: ]+)[^&\s]+", r"\1<redacted>", message)
    return message
