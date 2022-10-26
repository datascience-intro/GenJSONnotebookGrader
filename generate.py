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
#course.to_nb()
course.makeAssignmentNotebook(assignment_number = 1,notebook_type='problem_solution')
