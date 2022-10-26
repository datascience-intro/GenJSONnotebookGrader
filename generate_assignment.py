from NotebookGrader import IDSCourse,DBCourse
def checkPython():
    import sys
    print("Python version")
    print (sys.version)
    print("Version info.")
    print (sys.version_info)
    import sys
    print(sys.executable)

course = DBCourse()

course.makeAssignmentNotebook(assignment_number = 1,notebook_type='problem') # problem always comes with test # test and TEST are different things.
course.makeAssignmentNotebook(assignment_number = 1,notebook_type='problem_TEST')
course.makeAssignmentNotebook(assignment_number = 1,notebook_type='problem_solution')
course.makeAssignmentNotebook(assignment_number = 1,notebook_type='problem_solution_TEST')
course.makeAssignmentNotebook(assignment_number = 1,notebook_type='solution')
course.makeAssignmentNotebook(assignment_number = 1,notebook_type='solution_TEST')
course.makeAssignmentNotebook(assignment_number = 1,notebook_type='TEST')

# course.makeAssignmentNotebook(assignment_number = 2,notebook_type='problem') # problem always comes with test # test and TEST are different things.
# course.makeAssignmentNotebook(assignment_number = 2,notebook_type='problem_TEST')
# course.makeAssignmentNotebook(assignment_number = 2,notebook_type='problem_solution')
# course.makeAssignmentNotebook(assignment_number = 2,notebook_type='problem_solution_TEST')
# course.makeAssignmentNotebook(assignment_number = 2,notebook_type='solution')
# course.makeAssignmentNotebook(assignment_number = 2,notebook_type='solution_TEST')
# course.makeAssignmentNotebook(assignment_number = 2,notebook_type='TEST')

# course.makeAssignmentNotebook(assignment_number = 3,notebook_type='problem')
# course.makeAssignmentNotebook(assignment_number = 3,notebook_type='problem_TEST')
# course.makeAssignmentNotebook(assignment_number = 3,notebook_type='solution')
# course.makeAssignmentNotebook(assignment_number = 3,notebook_type='solution_TEST')

# course.makeAssignmentNotebook(assignment_number = 4,notebook_type='problem')
# course.makeAssignmentNotebook(assignment_number = 4,notebook_type='problem_TEST')
# course.makeAssignmentNotebook(assignment_number = 4,notebook_type='problem_solution')
# course.makeAssignmentNotebook(assignment_number = 4,notebook_type='problem_solution_TEST')
