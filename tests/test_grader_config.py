from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from contextlib import redirect_stdout

import nbformat

import Grader
from NotebookGrader.grader_config import (
    DEFAULT_POLL_INTERVAL_SECONDS,
    GraderConfigError,
    ensure_local_config_is_private,
    load_grader_config,
    redact_error,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class GraderConfigTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="grader-config-tests-")
        self.root = Path(self.temporary.name)
        self.source_dir = self.root / "master" / "jp"
        self.data_dir = self.source_dir / "data"
        self.install_dir = self.root / "GenerateMaterial" / "Assignments"
        self.data_dir.mkdir(parents=True)
        self.install_dir.mkdir(parents=True)
        (self.source_dir / "Utils.py").write_text("# utility\n", encoding="utf-8")
        (self.data_dir / "fixture.txt").write_text("data\n", encoding="utf-8")

        source = nbformat.v4.new_notebook(
            cells=[nbformat.v4.new_markdown_cell("# Canonical Assignment 1")]
        )
        self.source_path = self.source_dir / "Assignment_1.ipynb"
        nbformat.write(source, self.source_path)

        metadata = {
            "lx_assignment_type": "ASSIGNMENT",
            "lx_assignment_number": "1",
            "lx_problem_number": "1",
            "lx_problem_points": "24",
            "deletable": False,
        }
        problem_metadata = dict(metadata, lx_problem_cell_type="PROBLEM")
        test_metadata = dict(metadata, lx_problem_cell_type="TEST")
        installed = nbformat.v4.new_notebook(
            metadata={
                "lx_assignment_number": 1,
                "lx_course_number": "TEST101",
                "lx_course_name": "Test course",
                "lx_course_instance": "2026",
            },
            cells=[
                nbformat.v4.new_code_cell("answer = None", metadata=problem_metadata),
                nbformat.v4.new_code_cell("local_points = 24", metadata=test_metadata),
            ],
        )
        self.installed_path = self.install_dir / "Assignment_1_problem_TEST.ipynb"
        nbformat.write(installed, self.installed_path)
        self._write_manifest()
        self.config_path = self.root / "configGrader.json"
        self._write_config()

    def tearDown(self):
        self.temporary.cleanup()

    def _write_manifest(self, releases=(1,), installed_digest=None, source_digest=None):
        installed_digest = installed_digest or file_sha256(self.installed_path)
        source_digest = source_digest or file_sha256(self.source_path)
        assignments = {}
        if 1 in releases:
            assignments["1"] = {
                "problem_TEST": self.installed_path.name,
                "sha256": installed_digest,
                "source_sha256": source_digest,
            }
        manifest = {
            "schema_version": 1,
            "release_assignments": list(releases),
            "assignments": assignments,
        }
        (self.install_dir / "grader-manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )

    def _write_config(self):
        config = {
            "course": 123456,
            "API_URL": "https://uppsala.instructure.com",
            "API_KEY": "12345~private-test-token",
            "API_KEY_OWNER": "Test owner",
            "timezone": "Europe/Stockholm",
            "poll_interval_seconds": DEFAULT_POLL_INTERVAL_SECONDS,
            "docker_image": "itds-autograde:latest",
            "source_dir": "master/jp",
            "data_dir": "master/jp/data",
            "utils_file": "master/jp/Utils.py",
            "grader_manifest": "GenerateMaterial/Assignments/grader-manifest.json",
            "Assignments": [
                {
                    "number": 1,
                    "name": "Autograded assignment 1",
                    "studium_id": 123451,
                    "master_filename": "GenerateMaterial/Assignments/Assignment_1_problem_TEST.ipynb",
                    "start_date": "2026-08-31",
                    "end_date": "2026-09-25",
                }
            ],
        }
        self.config_path.write_text(json.dumps(config), encoding="utf-8")

    def _load(self, **kwargs):
        return load_grader_config(
            self.config_path,
            check_git=False,
            check_runtime=False,
            **kwargs,
        )

    def test_valid_manifest_selects_released_master_and_timezone_window(self):
        configuration = self._load(assignment_number=1)
        self.assertEqual(configuration.released_assignments, (1,))
        self.assertEqual(configuration.poll_interval_seconds, 43200)
        self.assertEqual(configuration.timezone.key, "Europe/Stockholm")
        start, end = configuration.assignments[0].window(configuration.timezone)
        self.assertEqual((start.hour, start.minute), (0, 1))
        self.assertEqual((end.hour, end.minute), (23, 59))
        self.assertNotIn("private-test-token", repr(configuration))

    def test_installed_master_hash_mismatch_is_rejected(self):
        self._write_manifest(installed_digest="0" * 64)
        with self.assertRaisesRegex(GraderConfigError, "master hash"):
            self._load(assignment_number=1)

    def test_canonical_source_hash_mismatch_is_rejected(self):
        self._write_manifest(source_digest="0" * 64)
        with self.assertRaisesRegex(GraderConfigError, "source hash"):
            self._load(assignment_number=1)

    def test_unreleased_assignment_is_rejected(self):
        self._write_manifest(releases=())
        with self.assertRaisesRegex(GraderConfigError, "not released"):
            self._load(assignment_number=1)

    def test_local_config_must_be_ignored_and_untracked(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / ".gitignore").write_text("configGrader.json\n", encoding="utf-8")
        warning = ensure_local_config_is_private(self.config_path)
        self.assertIn("chmod 600", warning or "")
        subprocess.run(
            ["git", "-C", str(self.root), "add", "-f", "configGrader.json"],
            check=True,
        )
        with self.assertRaisesRegex(GraderConfigError, "tracked by Git"):
            ensure_local_config_is_private(self.config_path)

    def test_errors_are_redacted(self):
        token = "12345~super-secret"
        error = RuntimeError(
            f"failed https://example.invalid?access_token={token} API_KEY={token}"
        )
        message = redact_error(error, secrets=(token,))
        self.assertNotIn(token, message)
        self.assertIn("<redacted>", message)

    def test_grader_defaults_to_non_writing_mode(self):
        self.assertFalse(Grader.parse_args([]).apply)
        self.assertTrue(Grader.parse_args(["--apply"]).apply)
        self.assertTrue(Grader.parse_args(["--sharp"]).apply)

    def test_non_sharp_comment_force_cannot_write(self):
        from NotebookGrader.AutoGrader.AutoGrader import Autograder

        course = type(
            "Course",
            (),
            {"base_req_str": "https://example.invalid", "API_KEY": "secret"},
        )()
        assignment = type(
            "Assignment",
            (),
            {"attributes": {"id": 1, "name": "Assignment 1"}},
        )()
        grader = Autograder(course, assignment, "master.ipynb", sharp=False)
        with mock.patch("requests.put") as put:
            with redirect_stdout(io.StringIO()):
                grader._uploadSubmissionComment(1, "private feedback", force=True)
        put.assert_not_called()

    def test_controlled_dry_run_scores_one_submission_without_upload(self):
        from NotebookGrader.AutoGrader.AutoGrader import Autograder

        course = type(
            "Course",
            (),
            {"base_req_str": "https://example.invalid", "API_KEY": "secret"},
        )()
        assignment = type(
            "Assignment",
            (),
            {"attributes": {"id": 1, "name": "Assignment 1"}},
        )()
        grader = Autograder(course, assignment, "master.ipynb", sharp=False)

        def load_one_submission():
            grader.submissions = [
                {
                    "user_id": 7,
                    "attempt": 2,
                    "workflow_state": "submitted",
                    "missing": False,
                    "attachments": [{"filename": "submission.ipynb"}],
                }
            ]

        grader._getSubmissions = load_one_submission
        grader._gradeSubmission = mock.Mock(return_value=(24, "passed", True))
        grader._uploadSubmissionGrade = mock.Mock()
        with mock.patch("requests.put") as put, mock.patch("requests.post") as post:
            result = grader.gradeControlledSubmission(student_id=7)

        self.assertEqual(
            result,
            {"attempt": 2, "score": 24, "action": "graded-no-upload"},
        )
        grader._gradeSubmission.assert_called_once_with(
            grader.submissions[0], force=True
        )
        grader._uploadSubmissionGrade.assert_not_called()
        put.assert_not_called()
        post.assert_not_called()

    def test_help_does_not_require_canvas_connector(self):
        result = subprocess.run(
            [sys.executable, str(REPOSITORY_ROOT / "Grader.py"), "--help"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--apply", result.stdout)

    def test_importing_autograder_does_not_replace_tls_verification(self):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import ssl; before = ssl._create_default_https_context; "
                "import NotebookGrader.AutoGrader.AutoGrader; "
                "assert ssl._create_default_https_context is before",
            ],
            cwd=REPOSITORY_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
