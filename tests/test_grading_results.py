from contextlib import redirect_stdout
import copy
import io
import unittest
from unittest import mock

import nbformat

from NotebookGrader.AssignmentNotebook.IDSAssignmentNotebook import IDSAssignmentNotebook
from NotebookGrader.AutoGrader.IDSGrader import IDSAutoGrader


class GradingResultsTests(unittest.TestCase):
    def merged_notebook(self, broken=(), markdown=False):
        metadata = {
            'lx_course_number': 'TEST101',
            'lx_course_name': 'Test course',
            'lx_course_instance': '2026',
            'lx_assignment_number': 1,
        }
        student = nbformat.v4.new_notebook(metadata=metadata)
        master = nbformat.v4.new_notebook(metadata=metadata)
        for number, points in enumerate((4, 6, 4), start=1):
            problem = {
                'lx_assignment_type': 'ASSIGNMENT',
                'lx_assignment_number': '1',
                'lx_problem_number': str(number),
                'lx_problem_points': str(points),
                'lx_problem_cell_type': 'PROBLEM',
            }
            code = f'answer_{number} = {number}'
            master.cells.append(nbformat.v4.new_code_cell(code, metadata=problem))
            factory = nbformat.v4.new_code_cell
            if number in broken:
                if markdown:
                    factory = nbformat.v4.new_markdown_cell
                else:
                    code = 'raise ValueError("student code failed")'
            student.cells.append(factory(code, metadata=problem))
            master.cells.append(nbformat.v4.new_code_cell(
                f'# ASSIGNMENT 1, TEST {number}, POINTS {points}\n'
                f'local_points = {points} if answer_{number} == {number} else 0',
                metadata={**problem, 'lx_problem_cell_type': 'TEST'},
            ))
        return IDSAssignmentNotebook(notebook=student) + IDSAssignmentNotebook(notebook=master)

    def execute_fixture(self, merged):
        # Execute only the small synthetic Python fixtures above, never submissions.
        notebook = copy.deepcopy(merged.to_notebook())
        namespace = {}
        for cell in notebook.cells:
            if cell.cell_type != 'code':
                continue
            cell.outputs = []
            stream = io.StringIO()
            error = None
            try:
                with redirect_stdout(stream):
                    exec(cell.source, namespace)
            except Exception as exc:
                error = nbformat.v4.new_output(
                    'error', ename=type(exc).__name__, evalue=str(exc),
                    traceback=['PRIVATE TEST SOURCE: ' + cell.source],
                )
            if stream.getvalue():
                cell.outputs.append(nbformat.v4.new_output(
                    'stream', name='stdout', text=stream.getvalue(),
                ))
            if error:
                cell.outputs.append(error)
            cell.execution_count = 1
        return IDSAssignmentNotebook(notebook=notebook)

    def test_failed_or_markdown_problem_preserves_other_scores(self):
        for markdown in (False, True):
            for problem, lost_points in ((1, 4), (2, 6), (3, 4)):
                with self.subTest(markdown=markdown, problem=problem):
                    graded = self.execute_fixture(self.merged_notebook((problem,), markdown))
                    result, feedback = graded.extractResult()
                    self.assertEqual(float(result['lx_problem_total_scored_points']), 14 - lost_points)
                    self.assertEqual(float(result['lx_problem_total_possible_points']), 14)
                    self.assertIn(f'Problem {problem}', feedback)
                    self.assertIn('NameError', feedback)
                    self.assertIn('Markdown', feedback)
                    response = graded.to_response_notebook(result, feedback)
                    nbformat.validate(response)
                    for cell in response.cells:
                        if cell.metadata.get('lx_problem_cell_type') == 'TEST_OUTPUT':
                            self.assertEqual(cell.source, '')
                            self.assertNotIn('PRIVATE TEST SOURCE', str(cell.outputs))
                    self.assertIn('No points were recorded', nbformat.writes(response))

    def test_all_completed_tests_retain_full_score(self):
        graded = self.execute_fixture(self.merged_notebook())
        result, feedback = graded.extractResult()
        self.assertEqual(result['lx_problem_total_scored_points'], '14')
        self.assertEqual(result['lx_problem_total_possible_points'], '14')
        self.assertNotIn('No points were recorded', feedback)

    def test_single_problem(self):
        for broken in ((), (1,)):
            with self.subTest(broken=broken):
                merged = self.merged_notebook(broken, markdown=True)
                merged.notebook.cells = merged.notebook.cells[:2]
                graded = self.execute_fixture(merged)
                result, _ = graded.extractResult()
                self.assertEqual(result['lx_problem_total_scored_points'], '0' if broken else '4')
                self.assertEqual(result['lx_problem_total_possible_points'], '4')

    def test_stdout_before_error_does_not_count_as_a_completed_test(self):
        graded = self.execute_fixture(self.merged_notebook((3,), markdown=True))
        failed_test = graded.assignments[-1].TEST_Cells[0]
        failed_test.outputs.insert(0, nbformat.v4.new_output(
            'stream', name='stdout', text='Some checks passed before the error.\n',
        ))
        result, feedback = graded.extractResult()
        self.assertEqual(result['lx_problem_total_scored_points'], '10')
        self.assertIn('Some checks passed before the error.', feedback)
        self.assertIn('NameError', feedback)

    def test_all_tests_fail_returns_zero_out_of_full_maximum(self):
        graded = self.execute_fixture(self.merged_notebook((1, 2, 3), markdown=True))
        result, feedback = graded.extractResult()
        self.assertEqual(float(result['lx_problem_total_scored_points']), 0)
        self.assertEqual(float(result['lx_problem_total_possible_points']), 14)
        self.assertEqual(feedback.count('No points were recorded'), 3)

    def test_missing_test_output_keeps_completed_scores(self):
        graded = self.execute_fixture(self.merged_notebook())
        graded.assignments[-1].TEST_Cells[0].outputs = []
        result, feedback = graded.extractResult()
        self.assertEqual(float(result['lx_problem_total_scored_points']), 10)
        self.assertEqual(float(result['lx_problem_total_possible_points']), 14)
        self.assertIn('no score was produced', feedback)

    def test_split_stdout_and_decimal_scores(self):
        graded = self.execute_fixture(self.merged_notebook())
        for assignment in graded.assignments:
            if not assignment.amITEST():
                continue
            cell = assignment.TEST_Cells[0]
            points = cell.metadata.lx_problem_points
            cell.outputs = [
                nbformat.v4.new_output('stream', name='stderr', text='a warning\n'),
                nbformat.v4.new_output('stream', name='stdout', text='The number of points you have scored '),
                nbformat.v4.new_output('stream', name='stdout', text=f'for this problem is 0.1 out of {points}\n'),
            ]
        result, _ = graded.extractResult()
        self.assertEqual(result['lx_problem_total_scored_points'], '0.3')
        self.assertEqual(result['lx_problem_total_possible_points'], '14')

    def test_safe_grade_returns_response_for_incomplete_problem(self):
        merged = self.merged_notebook((3,), markdown=True)
        executed = self.execute_fixture(merged)
        auto = IDSAutoGrader(
            None, mock.Mock(attributes={'id': 1}), 'unused.ipynb', sharp=False,
        )
        with mock.patch.object(auto, 'prepareNotebookForGrading', return_value=merged), \
                mock.patch.object(auto, 'safeRunNotebook', return_value={
                    'stdout': nbformat.writes(executed.notebook),
                    'timeout': False, 'oom_killed': False, 'unknown_error': False,
                }):
            result = auto.safeGradeNotebook('student.ipynb', 'unused.ipynb')
        self.assertEqual(float(result['lx_problem_total_scored_points']), 10)
        self.assertEqual(float(result['lx_problem_total_possible_points']), 14)
        self.assertIsInstance(result['Response_Notebook'], dict)
        self.assertIn('NameError', result['text_response'])
        self.assertEqual(auto._problemScores(result['text_response']), [
            ('1', '4', '4'), ('2', '6', '6'), ('3', '0', '4'),
        ])
        nbformat.validate(result['Response_Notebook'])


if __name__ == '__main__':
    unittest.main()
