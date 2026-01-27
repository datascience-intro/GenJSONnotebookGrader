from NotebookGrader import IDSCourse
from NotebookGrader import IDSCourseNotebook,IDSExamNotebook
import os
# def checkPython():
#     import sys
#     print("Python version")
#     print (sys.version)
#     print("Version info.")
#     print (sys.version_info)
#     import sys
#     print(sys.executable)

master_notebook = 'Exam_master.ipynb'
problem_notebook = 'Exam_problem.ipynb'
solution_notebook = 'Exam_solution.ipynb'
test_notebook = 'Exam_problem_solution_TEST.ipynb'

def generate_problem():
    exam = IDSCourseNotebook(os.path.join(path,master_notebook))
    examN = IDSExamNotebook([exam],assignmentNumber='vB',examHeader=examHeader,examIDHeader=True)
    examN.to_nb(os.path.join(path,problem_notebook),notebook_type='problem')
def generate_test():
    exam = IDSCourseNotebook(os.path.join(path,master_notebook))
    examN = IDSExamNotebook([exam],assignmentNumber='vB',examHeader=examHeader)
    examN.to_nb(os.path.join(path,test_notebook),notebook_type='problem+solution+TEST')
def generate_solution():
    exam = IDSCourseNotebook(os.path.join(path,master_notebook))
    examN = IDSExamNotebook([exam],assignmentNumber='vB',examHeader=examHeader)
    examN.to_nb(os.path.join(path,solution_notebook),notebook_type='problem+solution')

if __name__ == '__main__':
    import sys
    args = sys.argv[1:]
    with open('examHeader.md',mode='r') as f:
        examHeader = f.read()
    path = args[0]
    # checkPython()
    print("Generating exam files in path: ",path)
    generate_problem()
    generate_test()
    generate_solution()