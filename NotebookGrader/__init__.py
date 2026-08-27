from .AssignmentNotebook.AssignmentNotebook import *
from .AssignmentNotebook.IDSAssignmentNotebook import *
from .AssignmentNotebook.DBAssignmentNotebook import *


def __getattr__(name):
    """Load grading classes only when a grader explicitly requests them.

    Notebook generation must not import Docker/runtime dependencies or mutate
    process-wide networking settings merely by importing ``NotebookGrader``.
    """

    if name == "Autograder":
        from .AutoGrader.AutoGrader import Autograder

        return Autograder
    if name == "DBAutoGrader":
        from .AutoGrader.DBGrader import DBAutoGrader

        return DBAutoGrader
    if name == "IDSAutoGrader":
        from .AutoGrader.IDSGrader import IDSAutoGrader

        return IDSAutoGrader
    raise AttributeError(name)
