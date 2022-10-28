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
    options = ["generate", "grading", "exit"]
    terminal_menu = TerminalMenu(options)
    menu_entry_index = terminal_menu.show()
    if (menu_entry_index == 0):
        menu_generate()
        menu_main()
    if (menu_entry_index == 1):
        menu_grade()
        menu_main()

def menu_generate():
    options = ["course notebooks", "assignment notebooks", "back"]
    terminal_menu = TerminalMenu(options)
    menu_entry_index = terminal_menu.show()
    if (menu_entry_index == 0):
        input("Code not integrated into CLI, press any key to go back")
    if (menu_entry_index == 1):
        menu_assignment_notebooks()

def menu_assignment_notebooks():
    options = ["assignment 1", "assignment 2", "assignment 3", "back"]
    terminal_menu = TerminalMenu(options)
    menu_entry_index = terminal_menu.show()
    if (menu_entry_index == 0):
        menu_choose_gen_type()
    if (menu_entry_index == 1):
        input("No assignment 2, press any key to go back")
    if (menu_entry_index == 2):
        input("No assignment 3, press any key to go back")


def menu_choose_gen_type():
    options = ["generate all", "problems", "solutions", "tests", "upload to dbc workspace", "back"]
    terminal_menu = TerminalMenu(options)
    menu_entry_index = terminal_menu.show()
    if (menu_entry_index == 0):
        download_master(conf,notebook_conf)
        course.makeAssignmentNotebook(assignment_number = 1,notebook_type='problem') 
        course.makeAssignmentNotebook(assignment_number = 1, notebook_type='solution') 
        course.makeAssignmentNotebook(assignment_number = 1, notebook_type='problem_TEST')
        input("Press Enter to continue...")
        menu_choose_gen_type()
    if (menu_entry_index == 1):
        course.makeAssignmentNotebook(assignment_number = 1,notebook_type='problem') 
        menu_choose_gen_type()
    if (menu_entry_index == 2):
        course.makeAssignmentNotebook(assignment_number = 1, notebook_type='solution') 
        menu_choose_gen_type()
    if (menu_entry_index == 3):
        course.makeAssignmentNotebook(assignment_number = 1, notebook_type='problem_TEST') 
        menu_choose_gen_type()
    if (menu_entry_index == 4):
        upload_generated_assignments(conf,notebook_conf)
        input("Press Enter to continue...")
        menu_choose_gen_type()


def menu_grade():
    #options = [str(ass) for ass in course.assignments]
    #terminal_menu = TerminalMenu(options)
    #menu_entry_index = terminal_menu.show()
    #if (menu_entry_index == 0):
    os.system("python3 Grader.py")




def upload():
    # use dbc-rest wrapper to upload the generated book
    return 0




menu_main()