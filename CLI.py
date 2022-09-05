from CanvasInterface import Course
import json
from NotebookGrader import Autograder

with open("configGrader.json","r") as f:
    conf = json.load(f)

course = Course(API_URL=conf['API_URL'],API_KEY=conf['API_KEY'],COURSE_ID=conf['course'])

from simple_term_menu import TerminalMenu
def clear():
    import os
    os.system('cls||clear')

def greet():
    clear()
    print("Welcome to the command line interface for managing the Course on Studium!")
    options = ["List assignments","Exit"]
    terminal_menu = TerminalMenu(options)
    menu_entry_index = terminal_menu.show()
    if (menu_entry_index == 0): # listAssignments
        listAssignments()
        greet()

def listAssignments():
    options = [ass.name() for ass in course.assignments]
    terminal_menu = TerminalMenu(options)
    menu_entry_index = terminal_menu.show()
    chosenAssignment=course.assignments[menu_entry_index]
    manageAssignment(chosenAssignment)

def manageAssignment(assignment):
    print(assignment)
    options = ["List Submissions", "Download Submission","Back"]

    # Time to find the assignment also in the config
    ass_confs = [assignment_conf for assignment_conf in conf['Assignments'] if assignment_conf['name'] == assignment.name()]
    if (len(ass_confs) == 0):
        print("No config for this assignment!")
        wait = input("Press Enter to continue.")
        return

    terminal_menu = TerminalMenu(options)
    menu_entry_index = terminal_menu.show()
    if (menu_entry_index == 2):
        return

    auto = Autograder.makeAutoGrader(course,assignment,ass_confs[0],sharp=False)

    if (menu_entry_index == 0): # Chosen to List
        listSubmissions(assignment)
        manageAssignment(assignment)
    elif (menu_entry_index == 1):
        downloadSubmissionMenu(auto,assignment)
        manageAssignment(assignment)

def downloadSubmissionMenu(auto,assignment):
    print("Choose submission to download")
    chosen_submission = listSubmissions(assignment)
    user_id = chosen_submission['user_id']
    auto.getStudentSubmission(user_id)

    #Autograder.makeAutoGrader(course,assignment,assignment_conf,sharp=True)

def listSubmissions(assignment):
    submissions = course.getAssignmentSubmissions(assignment.id())
    options = []
    filtered_submissions = []
    for submission in submissions:
        if (submission['submitted_at'] != None):
            user_id = submission['user_id']
            user = course.get_user(user_id)
            score = submission['score']
            options.append("%s, user_id: %s, score:%s" % (user['name'],user_id,score))
            filtered_submissions.append(submission)
    if len(options) == 0:
        print("No submissions")
        pause()
        return -1
    terminal_menu = TerminalMenu(options)
    menu_entry_index = terminal_menu.show()
    return filtered_submissions[menu_entry_index]

greet()
