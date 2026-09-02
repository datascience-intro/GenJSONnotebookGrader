from CanvasInterface import Course
import json
from pathlib import Path
from NotebookGrader import Autograder
from NotebookGrader.AssignmentNotebook.IDSAssignmentNotebook import IDSCourse
from NotebookGrader.generation_cli import assignment_main

BASE_DIR = Path(__file__).resolve().parent
USERS_PATH = BASE_DIR / "users.json"

with (BASE_DIR / "configGrader.json").open("r", encoding="utf-8") as f:
    conf = json.load(f)

course = Course(API_URL=conf['API_URL'],API_KEY=conf['API_KEY'],COURSE_ID=conf['course'])

from simple_term_menu import TerminalMenu
def clear():
    import os
    os.system('cls||clear')

def pause():
    x = input('Press any key to continue')

def get_user(course,user_id):
    user_id = str(user_id)
    if user_id in user_dict:
        return user_dict[user_id]
    else:
        user = course.get_user(user_id)
        user_dict[user_id] = user['name']
        save_users()
        return user['name']


try:
    with USERS_PATH.open("r", encoding="utf-8") as f:
        user_dict = json.load(f)
        if not isinstance(user_dict, dict):
            user_dict = {}
except (FileNotFoundError, json.JSONDecodeError):
    user_dict = {}

def save_users():
    with USERS_PATH.open("w", encoding="utf-8") as f:
        json.dump(user_dict, f)

def clear_downloads():
    # Delete files in StudentSubmission
    import os
    path = 'StudentSubmission'
    ss = os.listdir(path)
    for f in ss:
        if (f[-5:] == 'ipynb'):
            os.remove(os.path.join(path,f))
            print(os.path.join(path,f))
    # Delete files in StudentWTest
    path = 'SolutionWTest'
    ss = os.listdir(path)
    for f in ss:
        if (f[-5:] == 'ipynb'):
            os.remove(os.path.join(path,f))
            print(os.path.join(path,f))

def greet():
    clear()
    print("Welcome to the command line interface for managing the Course on Studium!")
    options = ["Generate Material and Assignments","List assignments","Clear Downloads","Exit"]
    terminal_menu = TerminalMenu(options)
    menu_entry_index = terminal_menu.show()
    if (menu_entry_index == 0): # Generate Material and Assignments
        menu_generate()
        greet()
    if (menu_entry_index == 1): # listAssignments
        listAssignments()
        greet()
    if (menu_entry_index == 2): # Clear Downloads
        clear_downloads()
        pause()
        greet()

def menu_generate():
    options = [
        "Generate Material",
        "Generate Released Assignments",
        "Generate Assignment by Number",
        "Back",
    ]
    terminal_menu = TerminalMenu(options)
    menu_entry_index = terminal_menu.show()
    if (menu_entry_index == 0):
        idsCourse = IDSCourse()
        idsCourse.to_nb()
        input("Material generated! Press Enter to continue.")
    elif (menu_entry_index == 1):
        assignment_main([])
        input("Press Enter to continue.")
    elif (menu_entry_index == 2):
        assignment_number = input("Assignment number: ").strip()
        if not assignment_number.isdigit():
            print("Assignment number must be a positive integer.")
        else:
            assignment_main(["--assignment", assignment_number])
        input("Press Enter to continue.")


def listAssignments():
    options = [ass.name() for ass in course.assignments]
    terminal_menu = TerminalMenu(options)
    menu_entry_index = terminal_menu.show()
    chosenAssignment=course.assignments[menu_entry_index]
    manageAssignment(chosenAssignment)

def manageAssignment(assignment):
    print(assignment)
    options = ["List Submissions", "Download Submission","Inject tests into submission","Back"]

    # Time to find the assignment also in the config
    ass_confs = [assignment_conf for assignment_conf in conf['Assignments'] if assignment_conf['name'] == assignment.name()]
    if (len(ass_confs) == 0):
        print("No config for this assignment!")
        wait = input("Press Enter to continue.")
        return

    terminal_menu = TerminalMenu(options)
    menu_entry_index = terminal_menu.show()
    if (menu_entry_index == 3):
        return

    auto = Autograder.makeAutoGrader(course,assignment,ass_confs[0],sharp=False)

    if (menu_entry_index == 0): # Chosen to List
        listSubmissions(assignment)
        manageAssignment(assignment)
    elif (menu_entry_index == 1):
        downloadSubmissionMenu(auto,assignment)
        manageAssignment(assignment)
    elif (menu_entry_index == 2):
        manageSubmissions(assignment,auto)
        manageAssignment(assignment)

def manageSubmissions(assignment,auto):
    import os
    ss = os.listdir('StudentSubmission/')
    print(ss)
    ss = [sub for sub in ss if sub[-6:] == ".ipynb"]
    if (len(ss) > 0):
        print("Choose downloaded submission to process")
        terminal_menu = TerminalMenu(ss)
        menu_entry_index = terminal_menu.show()
        injectTests(assignment,'StudentSubmission/'+ss[menu_entry_index],auto)
    else:
        print("No downloaded submissions!")
        wait = input("Press Enter to continue.")

def yesNo():
    """Returns 1 for Yes and 0 for No
    """
    options=["Yes","No"]
    terminal_menu = TerminalMenu(options)
    menu_entry_index = terminal_menu.show()
    return 1-menu_entry_index

def injectTests(assignment, ss, auto):
    print("You chose %s: Do you want to inject tests?" % ss)
    if (yesNo()):
        # Inject the tests
        student_id = ss.split('/')[1].split('_')[0]
        student_name = ss.split('/')[1].split('_')[1][:-6]
        auto.prepareNotebookForGrading(ss,auto.master_nb_filename,student_id = student_id,student_name = get_user(course,student_id))

def downloadSubmissionMenu(auto,assignment):
    print("Choose submission to download")
    chosen_submission = listSubmissions(assignment)
    user_id = chosen_submission['user_id']
    auto.getStudentSubmission(user_id,get_user(course,user_id))

    #Autograder.makeAutoGrader(course,assignment,assignment_conf,sharp=True)

def listSubmissions(assignment):
    submissions = course.getAssignmentSubmissions(assignment.id())
    options = []
    filtered_submissions = []
    for submission in submissions:
        if (submission['submitted_at'] != None):
            user_id = submission['user_id']
            user = get_user(course,user_id)#course.get_user(user_id)
            score = submission['score']
            options.append("%s, user_id: %s, score:%s" % (user,user_id,score))
            filtered_submissions.append(submission)
    if len(options) == 0:
        print("No submissions")
        pause()
        return -1
    terminal_menu = TerminalMenu(options)
    menu_entry_index = terminal_menu.show()
    return filtered_submissions[menu_entry_index]


greet()
