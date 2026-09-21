import unittest
from unittest import mock

import nbformat

from NotebookGrader.AssignmentNotebook.AssignmentNotebook import AssignmentNotebook
from NotebookGrader.AutoGrader.IDSGrader import IDSAutoGrader


class NotebookMetadataTests(unittest.TestCase):
    def setUp(self):
        self.metadata = {
            'lx_course_number': 'TEST101',
            'lx_course_name': 'Test course',
            'lx_course_instance': '2026',
            'lx_assignment_number': 1,
        }
        self.reader = AssignmentNotebook()

    def test_valid_jupyter_and_databricks_metadata(self):
        for metadata_name in ('metadata', 'notebookMetadata'):
            with self.subTest(metadata_name=metadata_name):
                details, number = self.reader._extractCourseDetails({metadata_name: self.metadata})
                self.assertEqual(details, {
                    'CourseID': 'TEST101', 'CourseName': 'Test course', 'CourseInstance': '2026',
                })
                self.assertEqual(number, 1)

    def test_missing_or_empty_field_names_the_field_and_explains_recovery(self):
        for field in self.metadata:
            for value in ('absent', None, ''):
                with self.subTest(field=field, value=value):
                    metadata = dict(self.metadata)
                    if value == 'absent':
                        metadata.pop(field)
                    else:
                        metadata[field] = value
                    with self.assertRaises(ValueError) as error:
                        self.reader._extractCourseDetails({'metadata': metadata})
                    message = str(error.exception)
                    self.assertIn(field, message)
                    self.assertIn('original assignment notebook', message)
                    self.assertIn('existing answer cells', message)
                    self.assertIn('contact course staff', message)

    def test_all_missing_fields_are_reported_together(self):
        with self.assertRaises(ValueError) as error:
            self.reader._extractCourseDetails({'metadata': {}})
        for field in self.metadata:
            self.assertIn(field, str(error.exception))

    def test_submission_feedback_reports_metadata_error_before_execution(self):
        notebook = nbformat.v4.new_notebook(metadata=self.metadata)
        del notebook.metadata['lx_course_number']
        grader = IDSAutoGrader(
            mock.Mock(), mock.Mock(attributes={'id': 1, 'name': 'Assignment 1'}),
            'master.ipynb', sharp=False,
        )
        submission = {
            'user_id': 7, 'attempt': 1, 'workflow_state': 'submitted',
            'grade': None, 'grade_matches_current_submission': False, 'missing': False,
            'attachments': [{'filename': 'submission.ipynb', 'url': 'https://example.invalid/file'}],
        }
        with mock.patch('urllib.request.urlretrieve'), \
                mock.patch.object(AssignmentNotebook, '_load_notebook', return_value=notebook), \
                mock.patch.object(grader, 'safeRunNotebook') as execute, \
                mock.patch.object(grader, 'writeResponseFile') as write_response:
            grade, comment, update, response_ready, grading_error = grader._gradeSubmission(submission)
        self.assertEqual(grade, 0)
        self.assertTrue(update)
        self.assertFalse(response_ready)
        self.assertTrue(grading_error)
        self.assertIn('Reason: Your notebook is missing required course/assignment metadata: lx_course_number.', comment)
        self.assertIn('copy your answers into its existing answer cells', comment)
        self.assertNotIn("'CourseID'", comment)
        execute.assert_not_called()
        write_response.assert_not_called()


if __name__ == '__main__':
    unittest.main()
