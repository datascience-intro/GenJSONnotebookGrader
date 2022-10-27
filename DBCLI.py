import os
import json
from simple_term_menu import TerminalMenu
from NotebookGrader import DBCourse, download_master, upload_generated_assignments

with open("configGrader.json", "r") as f:
    conf = json.load(f)

with open("configNotebooks.json", "r") as f:
    notebook_conf = json.load(f)

with open("users.json", "r") as f:
    user_dict = json.load(f)


download_master(conf,notebook_conf)
course = DBCourse()


def clear():
    os.system('cls||clear')

def menu_main():
    clear()
    print("Welcome to the command line interface for managing the Course on Studium!")
    options = ["Generate", "Grade", "Exit"]
    terminal_menu = TerminalMenu(options)
    menu_entry_index = terminal_menu.show()
    if (menu_entry_index == 0):
        menu_generate()
        menu_main()
    if (menu_entry_index == 1):
        menu_grade()
        menu_main()

def menu_generate():
    options = ["generate all", "problems", "solutions", "tests", "back"]
    terminal_menu = TerminalMenu(options)
    menu_entry_index = terminal_menu.show()
    if (menu_entry_index == 0):
        download_master(conf,notebook_conf)
        course.makeAssignmentNotebook(assignment_number = 1,notebook_type='problem') 
        course.makeAssignmentNotebook(assignment_number = 1, notebook_type='solution') 
        course.makeAssignmentNotebook(assignment_number = 1, notebook_type='problem_TEST')
        input("Press Enter to continue...")
        upload_generated_assignments(conf,notebook_conf)
        input("Press Enter to continue...") 
    if (menu_entry_index == 1):
        course.makeAssignmentNotebook(assignment_number = 1,notebook_type='problem') 
    if (menu_entry_index == 2):
        course.makeAssignmentNotebook(assignment_number = 1, notebook_type='solution') 
    if (menu_entry_index == 3):
        course.makeAssignmentNotebook(assignment_number = 1, notebook_type='problem_TEST') 


def menu_grade():
    options = [str(ass) for ass in course.assignments]
    terminal_menu = TerminalMenu(options)
    menu_entry_index = terminal_menu.show()
    if (menu_entry_index == 0):
        os.system("python3 Grader.py")




def upload():
    # use dbc-rest wrapper to upload the generated book
    return 0




menu_main()