from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import nbformat

from NotebookGrader.generation_config import GenerationConfigError, load_generation_config


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
STUDENT_SCRIPT = REPOSITORY_ROOT / "generateIDSNotebooks.py"
PRIVATE_SCRIPT = REPOSITORY_ROOT / "generateIDSAssignmentMasterNotebooks.py"


class GenerationCLITests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="genjson-tests-")
        self.root = Path(self.temporary.name)
        self.masters = self.root / "masters"
        self.masters.mkdir()
        self._write_masters()

    def tearDown(self):
        self.temporary.cleanup()

    def _write_masters(self):
        lecture = nbformat.v4.new_notebook(
            cells=[nbformat.v4.new_markdown_cell("# Example lecture")]
        )
        nbformat.write(lecture, self.masters / "Lecture.ipynb")

        assignment = nbformat.v4.new_notebook(
            cells=[
                nbformat.v4.new_code_cell(
                    "# ASSIGNMENT 1, PROBLEM 1, POINTS 24\nanswer = None"
                ),
                nbformat.v4.new_code_cell(
                    "# ASSIGNMENT 1, SOLUTION 1, POINTS 24\nanswer = 42"
                ),
                nbformat.v4.new_code_cell(
                    "# ASSIGNMENT 1, Test 1, POINTS 24\nassert answer is not None"
                ),
                nbformat.v4.new_code_cell(
                    "# ASSIGNMENT 1, TEST 1, POINTS 24\nlocal_points = 24"
                ),
            ]
        )
        nbformat.write(assignment, self.masters / "Assignment_1.ipynb")
        assignment_2 = nbformat.v4.new_notebook(
            cells=[
                nbformat.v4.new_code_cell(
                    cell.source.replace("ASSIGNMENT 1", "ASSIGNMENT 2")
                )
                for cell in assignment.cells
            ]
        )
        nbformat.write(assignment_2, self.masters / "Assignment_2.ipynb")

    def _config(self, releases):
        return {
            "master_notebooks": ["Lecture", "Assignment_1", "Assignment_2"],
            "notebook_file_extension": "ipynb",
            "notebook_folder": "masters",
            "target_notebook_folder": "student",
            "target_assignment_master_folder": "private",
            "target_notebook_book_folder": "book",
            "assignments": releases,
            "CourseID": "TEST101",
            "CourseName": "Test course",
            "CourseInstance": "2026",
        }

    def _write_config(self, releases, filename="config.json"):
        path = self.root / filename
        path.write_text(json.dumps(self._config(releases)), encoding="utf-8")
        return path

    def _run(self, script, config, *extra):
        return subprocess.run(
            [
                sys.executable,
                str(script),
                "--config",
                str(config),
                *extra,
            ],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_empty_release_generates_placeholder_and_no_private_variants(self):
        config = self._write_config([])
        student = self._run(STUDENT_SCRIPT, config)
        self.assertEqual(student.returncode, 0, student.stderr)
        assignment_path = self.root / "student" / "Assignment_1.ipynb"
        generated = nbformat.read(assignment_path, as_version=4)
        nbformat.validate(generated)
        self.assertEqual(len(generated.cells), 1)
        self.assertFalse(
            any("lx_problem_cell_type" in cell.metadata for cell in generated.cells)
        )

        private = self._run(PRIVATE_SCRIPT, config)
        self.assertEqual(private.returncode, 0, private.stderr)
        self.assertTrue((self.root / "private").is_dir())
        self.assertEqual(list((self.root / "private").glob("*.ipynb")), [])

    def test_first_release_generates_student_and_four_private_variants(self):
        config = self._write_config([1])
        student = self._run(STUDENT_SCRIPT, config)
        private = self._run(PRIVATE_SCRIPT, config)
        self.assertEqual(student.returncode, 0, student.stderr)
        self.assertEqual(private.returncode, 0, private.stderr)

        released = nbformat.read(
            self.root / "student" / "Assignment_1.ipynb", as_version=4
        )
        student_types = {
            cell.metadata.get("lx_problem_cell_type")
            for cell in released.cells
            if "lx_problem_cell_type" in cell.metadata
        }
        self.assertIn("PROBLEM", student_types)
        self.assertIn("Test", student_types)
        self.assertNotIn("SOLUTION", student_types)
        self.assertNotIn("TEST", student_types)

        expected = {
            "Assignment_1_problem.ipynb",
            "Assignment_1_problem_TEST.ipynb",
            "Assignment_1_solution_TEST.ipynb",
            "Assignment_1_problem_solution.ipynb",
        }
        self.assertEqual(
            {path.name for path in (self.root / "private").glob("*.ipynb")},
            expected,
        )
        for filename in expected:
            nbformat.validate(nbformat.read(self.root / "private" / filename, as_version=4))

    def test_private_cli_can_generate_an_unreleased_assignment_explicitly(self):
        config = self._write_config([])
        result = self._run(PRIVATE_SCRIPT, config, "--assignment", "2")
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = {
            f"Assignment_2_{notebook_type}.ipynb"
            for notebook_type in (
                "problem",
                "problem_TEST",
                "solution_TEST",
                "problem_solution",
            )
        }
        self.assertEqual(
            {path.name for path in (self.root / "private").glob("*.ipynb")},
            expected,
        )

    def test_explicit_private_assignment_must_have_a_configured_master(self):
        raw = self._config([])
        raw["master_notebooks"] = ["Lecture", "Assignment_1"]
        config = self.root / "config.json"
        config.write_text(json.dumps(raw), encoding="utf-8")
        result = self._run(PRIVATE_SCRIPT, config, "--assignment", "2")
        self.assertEqual(result.returncode, 2)
        self.assertIn("selected assignments have no master", result.stderr)

    def test_check_and_list_do_not_create_output_directories(self):
        config = self._write_config([1])
        for script in (STUDENT_SCRIPT, PRIVATE_SCRIPT):
            result = self._run(script, config, "--check")
            self.assertEqual(result.returncode, 0, result.stderr)
            listed = self._run(script, config, "--list")
            self.assertEqual(listed.returncode, 0, listed.stderr)
            self.assertIn(str(self.masters / "Lecture.ipynb"), listed.stdout)
        self.assertFalse((self.root / "student").exists())
        self.assertFalse((self.root / "private").exists())

    def test_cli_overrides_are_resolved_from_an_arbitrary_working_directory(self):
        config = self._write_config([1])
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        student_output = self.root / "explicit-student"
        private_output = self.root / "explicit-private"
        result = subprocess.run(
            [
                sys.executable,
                str(STUDENT_SCRIPT),
                "--config",
                str(config),
                "--source-dir",
                str(self.masters),
                "--output-dir",
                str(student_output),
                "--assignment-output-dir",
                str(private_output),
            ],
            cwd=elsewhere,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((student_output / "Lecture.ipynb").is_file())

    def test_invalid_release_and_duplicate_master_fail_before_parsing(self):
        for releases in ([2], [1, 3], [2, 1], [1, 1], [1, 2, 3, 4, 5]):
            path = self._write_config(releases)
            with self.subTest(releases=releases):
                with self.assertRaises(GenerationConfigError):
                    load_generation_config(path)

        invalid = self._config([])
        invalid["master_notebooks"] = ["Lecture", "Lecture.ipynb"]
        path = self.root / "duplicate.json"
        path.write_text(json.dumps(invalid), encoding="utf-8")
        with self.assertRaises(GenerationConfigError):
            load_generation_config(path)

    def test_importing_generation_package_does_not_import_live_grader(self):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys, NotebookGrader; "
                "assert 'NotebookGrader.AutoGrader.AutoGrader' not in sys.modules",
            ],
            cwd=REPOSITORY_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_repeated_student_and_private_generation_is_byte_identical(self):
        config = self._write_config([1])
        student_directories = (self.root / "student-a", self.root / "student-b")
        private_directories = (self.root / "private-a", self.root / "private-b")
        for destination in student_directories:
            result = self._run(
                STUDENT_SCRIPT, config, "--output-dir", str(destination)
            )
            self.assertEqual(result.returncode, 0, result.stderr)
        for destination in private_directories:
            result = self._run(
                PRIVATE_SCRIPT,
                config,
                "--assignment-output-dir",
                str(destination),
            )
            self.assertEqual(result.returncode, 0, result.stderr)

        for first, second in (student_directories, private_directories):
            first_bytes = {
                path.name: path.read_bytes() for path in first.glob("*.ipynb")
            }
            second_bytes = {
                path.name: path.read_bytes() for path in second.glob("*.ipynb")
            }
            self.assertEqual(first_bytes, second_bytes)
            for path in first.glob("*.ipynb"):
                notebook = nbformat.read(path, as_version=4)
                nbformat.validate(notebook)
                identifiers = [cell.id for cell in notebook.cells]
                self.assertEqual(len(identifiers), len(set(identifiers)))

    def test_release_gate_changes_only_semantically_changed_student_notebook(self):
        empty_config = self._write_config([], "empty.json")
        released_config = self._write_config([1], "released.json")
        empty_output = self.root / "empty-student"
        released_output = self.root / "released-student"
        empty = self._run(
            STUDENT_SCRIPT, empty_config, "--output-dir", str(empty_output)
        )
        released = self._run(
            STUDENT_SCRIPT,
            released_config,
            "--output-dir",
            str(released_output),
        )
        self.assertEqual(empty.returncode, 0, empty.stderr)
        self.assertEqual(released.returncode, 0, released.stderr)

        for unchanged in ("Lecture.ipynb", "Assignment_2.ipynb"):
            self.assertEqual(
                (empty_output / unchanged).read_bytes(),
                (released_output / unchanged).read_bytes(),
                unchanged,
            )
        self.assertNotEqual(
            (empty_output / "Assignment_1.ipynb").read_bytes(),
            (released_output / "Assignment_1.ipynb").read_bytes(),
        )


if __name__ == "__main__":
    unittest.main()
