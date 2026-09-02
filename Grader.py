#!/usr/bin/env python3
"""Run the Studium notebook grader safely; Canvas writes require ``--apply``."""

from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import sys
import time
from typing import Any, Sequence

from NotebookGrader.grader_config import (
    DEFAULT_POLL_INTERVAL_SECONDS,
    GraderAssignment,
    GraderConfiguration,
    GraderConfigError,
    load_grader_config,
    redact_error,
)


REPOSITORY_ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = REPOSITORY_ROOT / "configGrader.json"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--manifest",
        type=Path,
        help="override the installed grader-manifest.json path",
    )
    parser.add_argument(
        "--assignment",
        type=int,
        choices=(1, 2, 3, 4),
        help="run only one released assignment",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--apply",
        "--sharp",
        action="store_true",
        dest="apply",
        help="allow Canvas score, comment, and file writes",
    )
    mode.add_argument(
        "--dry-run",
        action="store_false",
        dest="apply",
        help="download and grade at most one controlled submission without writing Canvas",
    )
    parser.set_defaults(apply=False)
    parser.add_argument(
        "--submission-user",
        type=int,
        help="limit a grading round to one Canvas user ID",
    )
    parser.add_argument(
        "--poll-seconds",
        type=int,
        help=f"polling interval; default config value is {DEFAULT_POLL_INTERVAL_SECONDS}",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="perform at most one grading round and exit",
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="validate local config, installed masters, and runtime without contacting Canvas",
    )
    return parser.parse_args(argv)


def _canvas_assignment_id(assignment: Any) -> int | None:
    attributes = getattr(assignment, "attributes", {})
    value = attributes.get("id") if isinstance(attributes, dict) else None
    if value is None and hasattr(assignment, "id"):
        candidate = assignment.id
        value = candidate() if callable(candidate) else candidate
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _resolve_canvas_assignment(course: Any, configured: GraderAssignment) -> Any:
    matches = [
        assignment
        for assignment in course.assignments
        if getattr(assignment, "attributes", {}).get("name") == configured.name
    ]
    if len(matches) != 1:
        raise GraderConfigError(
            f"Canvas must contain exactly one assignment named {configured.name!r}"
        )
    assignment = matches[0]
    actual_id = _canvas_assignment_id(assignment)
    if configured.studium_id not in (None, 0) and actual_id != configured.studium_id:
        raise GraderConfigError(
            f"Canvas assignment ID does not match local config for assignment {configured.number}"
        )
    return assignment


def _runtime_mapping(configuration: GraderConfiguration) -> dict[str, str]:
    return {
        "docker_image": configuration.docker_image,
        "data_dir": str(configuration.data_dir),
        "utils_file": str(configuration.utils_file),
    }


def _build_autograder(
    course: Any,
    canvas_assignment: Any,
    configured: GraderAssignment,
    configuration: GraderConfiguration,
    *,
    apply: bool,
) -> Any:
    from NotebookGrader.AutoGrader.AutoGrader import Autograder

    assignment_config = {
        "name": configured.name,
        "master_filename": str(configured.master_path),
    }
    return Autograder.makeAutoGrader(
        course,
        canvas_assignment,
        assignment_config,
        conf=_runtime_mapping(configuration),
        sharp=apply,
    )


def _run_round(
    auto: Any,
    configured: GraderAssignment,
    *,
    apply: bool,
    submission_user: int | None,
) -> None:
    if not apply or submission_user is not None:
        result = auto.gradeControlledSubmission(student_id=submission_user)
        if result is None:
            print(f"assignment={configured.name!r} action=no-controlled-submission")
            return
        print(
            "assignment=%r attempt=%s score=%s action=%s"
            % (
                configured.name,
                result.get("attempt"),
                result.get("score"),
                result.get("action"),
            )
        )
        if not apply:
            print("feedback:")
            print(result.get("feedback", ""))
        return
    auto.grade()
    print(f"assignment={configured.name!r} action=live-round-complete")


def _run_assignment(
    auto: Any,
    configured: GraderAssignment,
    configuration: GraderConfiguration,
    *,
    apply: bool,
    submission_user: int | None,
    once: bool,
    poll_seconds: int,
) -> None:
    start, end = configured.window(configuration.timezone)
    while True:
        now = datetime.now(configuration.timezone)
        if now > end:
            print(
                f"assignment={configured.name!r} window_end={end.isoformat()} action=window-ended"
            )
            return
        if now < start:
            print(
                f"assignment={configured.name!r} window_start={start.isoformat()} action=waiting"
            )
            if once:
                return
            time.sleep(min(poll_seconds, max(1.0, (start - now).total_seconds())))
            continue

        _run_round(
            auto,
            configured,
            apply=apply,
            submission_user=submission_user,
        )
        if once:
            return
        remaining = max(1.0, (end - datetime.now(configuration.timezone)).total_seconds())
        time.sleep(min(poll_seconds, remaining))


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    configuration: GraderConfiguration | None = None
    try:
        if args.poll_seconds is not None and args.poll_seconds < 60:
            raise GraderConfigError("--poll-seconds must be at least 60")
        configuration = load_grader_config(
            args.config,
            assignment_number=args.assignment,
            manifest_path=args.manifest,
            check_git=True,
            check_runtime=True,
        )
        for dirname in ("StudentSubmission", "Response"):
            if not (REPOSITORY_ROOT / dirname).is_dir():
                raise GraderConfigError(f"required grader work directory is missing: {dirname}")
        if configuration.permission_warning:
            print(f"WARNING: {configuration.permission_warning}", file=sys.stderr)
        if args.preflight_only:
            selected = ",".join(str(item.number) for item in configuration.assignments)
            manifest = configuration.manifest_path or "disabled"
            print(
                f"Preflight passed: assignments=[{selected}] manifest={manifest}"
            )
            return 0

        # Imports and Canvas construction happen only after every local preflight.
        from CanvasInterface import Course

        os.chdir(REPOSITORY_ROOT)
        course = Course(
            API_URL=configuration.api_url,
            API_KEY=configuration.api_key,
            COURSE_ID=configuration.course_id,
        )
        poll_seconds = args.poll_seconds or configuration.poll_interval_seconds
        mode = "apply" if args.apply else "dry-run"
        print(
            f"grader mode={mode} timezone={configuration.timezone.key} poll_seconds={poll_seconds}"
        )
        for configured in configuration.assignments:
            canvas_assignment = _resolve_canvas_assignment(course, configured)
            auto = _build_autograder(
                course,
                canvas_assignment,
                configured,
                configuration,
                apply=args.apply,
            )
            _run_assignment(
                auto,
                configured,
                configuration,
                apply=args.apply,
                submission_user=args.submission_user,
                once=args.once,
                poll_seconds=poll_seconds,
            )
        return 0
    except KeyboardInterrupt:
        print("Grader stopped.", file=sys.stderr)
        return 130
    except Exception as error:
        secrets = (configuration.api_key,) if configuration is not None else ()
        print(
            f"ERROR {type(error).__name__}: {redact_error(error, secrets=secrets)}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
