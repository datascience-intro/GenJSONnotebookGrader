# AssignmentNotebook
This repository contains the module that allows you to read / extract / create assignment notebooks from master notebooks

We have a few classes that are interesting for the user

* All classes that start with IDS are derivative classes specifically coded for the Intro to Datascience and classes that start with DB are specifically coded for Databricks with support for python and scala.
* All DB-classes are derivative classes specifically coded for Databricks notebooks
* The classes that contains the name `Book` is to generate cleaned notebooks for `jupyter-book`

however

* DB-classes do not currently have support for the Databricks equivalents of IDSExamNotebook, IDSBookNotebook and IDSBook.
* After a big code-refactoring, IDSExamNotebook, IDSBookNotebook and IDSBook are not tested properly.

# Usage guide
## Creating the book

* There is currently no support for this in databricks, but these are not needed for the general process of maintaining grading of student assignments.
```python
from AssignmentNotebook import IDSBook

# This loads all the notebooks
book = IDSBook()
# This bookifyes the notebooks and produces and output into
# the folder specified in config.json
book.to_nb()
# The idea now is to run the

```


# Specific classes for Databricks and Intro to Data Science AssignmentNotebooks
## class DBCourse
```
Wrapper for the entire course. All details are in DBCourseDetails.

Parameters
----------
courseDetails : DBSCourseDetails
lectureNotebooks : dict('notebook_filename' : DBLectureNotebook)
    a dictionary of key,value being notebook filename and an DBLectureNotebook
assignments : dict('assignment number' : DBAssignmentNotebook)
    a dictionary of key,value being assingment number and DBAssignmentNotebook

Methods
-------
makeAssignmentNotebook(assignment_number,notebook_type='problem_solution_TEST')
    creates the AssignmentNotebook related to assignment_number of the specified
    notebook_type
to_nb()
    makes a lecture notebook out of all notebooks described in DBCourseDetails.
```

## class DB- and IDSCourseDetails(CourseDetails)
```
The specific details regarding the Intro to Data Science.
All the specifics are to be put inside the config.json inside the package

What needs to be specified in the configNotebooks.json are the following
{
  "master_notebooks":["Example_databricks_1"],
  "notebook_file_extension":"db",
  "notebook_folder":"../master/db",
  "target_notebook_folder":"lectures",
  "target_notebook_book_folder":"Notebooks",
  "assignments":[1],
  "CourseID":"1MS041",
  "CourseName":"Introduction to Data Science: A Comp-Math-Stat Approach",
  "CourseInstance":"2020"
}
```
> To generate several assignments at the same time, just add the master notebooks and assignment-number to the config.
"master_notebooks":["Example_databricks_1","Example_databricks_2"]
"assignments":[1,2]
> For the key `master_notebooks`, it is a list of names of master notebooks **WITHOUT** any file extension.
> For the key `notebook_file_extension`, it is a file extension of master notebooks. For databricks notebooks, specify `db`,and for Jupyter notebooks, specify `jp`.
> For the Key `notebook_folder`, it is a path to a directory that stores master notebooks. For databricks notebooks, they are stored in `master/db`, and for Jupyter notebooks, they are stored in `master/jp`. Different directory names or paths are also possible, if necessary.

# Specific classes creating a jupyter book for Intro to Data Science
## class IDSBookNotebook(CourseNotebook)
Specifically the method `_bookify` which is contains some code to make the
notebooks better suited for jupyter-book. This has no support for databricks yet, but is not needed in the process of maintaining the assignment system.
* Truncates the output to a few lines
* Truncates error messages by truncating the Traceback

## class IDSBook()
Pretty much the same as `IDSCourse` but for a jupyter book. No support for Databricks but is again not needed in the process of maintaining the assignment system.

# Generic classes for AssignmentNotebook
## class CourseNotebook
```
Represents a course notebooks


  Attributes
  ----------
  courseDetails : CourseDetails
  header : str
      the header string, to be put as the first cell when outputting
      as a notebook
  assignmentNumbers : [int]
      If there are assignment problems in this notebook, the assignment
      number/numbers will be stored here.
  assignmentCells : [nbformat cell]
      these are all the assignment related cells contained in this notebook
  notebook : nbformat.NotebookNode
      the raw notebook, if loaded from file
  nb_filename : str
      the filename of the raw notebook

  Methods
  -------
  getAssignments(assignmentNumber=0)
      returns the problems found in this courseNotebook related to
      assignmentNumber

  toLectureNotebook(skipAssignments=False)
      returns a nbformat.NotebookNode with the student ready notebook.
      skipAssignments is self explanatory.

  to_nb(target_filename,skipAssignments=False)
      writes the notebook to file, it writes the same as
      toLectureNotebook(skipAssignments) to `target_filename`
```

## class AssignmentNotebook(CourseNotebook)
```
Represents an assignment notebook

    Parameters
    ----------
    assignmentNumber : int
        The assignment number of this notebook
    courseNotebooks : [CourseNotebook]
        All the course notebooks that contains the assignments
    assignments : [Assignment]
        all the assignments in this assignment notebook

    Methods
    -------
    to_nb(target_filename,notebook_type='problem_solution_TEST')
        Creates a notebook and writes it to file.
    to_notebook(notebook_type='problem_solution_TEST')
        load a notebook file and turn it into a JSON-format
    __add__(assignmentNotebook)
        assignmentNotebook1 + assignmentNotebook2 yields a new AssignmentNotebook that has the entire
        assignmentNotebook1 + the TESTS from assignmentNotebook2
    numProblems()
        the number of Assignments in this AssignmentNotebook

    numTests()
        How many pure TEST Assignments we have

    extractResult()
        Extracts the result of a graded notebook
```

## class Assignment()
```
Represents a problem (or Assignment) in an AssignmentNotebook

    Parameters
    ----------
    PROBLEM_Cells : [dict]
        This is the list of all notebook cells that has the tag PROBLEM.
        This is the problem description and solution skeleton.
    SOLUTION_Cells : [dict]
        This is the list of all notebook cells that has the tag SOLUTION.
        These are the proposed solution cells.
    Test_Cells : [dict]
        This is the list of all notebook cells that has the tag Test. These
        are the self tests (local tests)
    TEST_Cells : [dict]
        This is the list of all notebook cells that has the tag TEST.
        These are the final tests for the assignment, there should actually only
        be one.

    Methods
    -------
    amITEST()
        returns if this is a TEST only assignment. I.e. there are no
        problem, solution, Test cells but only TEST cells.
```
