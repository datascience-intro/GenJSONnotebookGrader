import time
import json
from datetime import datetime
from CanvasInterface import Course
#from AutoGrader.AutoGrader import Autograder
from NotebookGrader import Autograder
MINUTE = 60
HOUR = MINUTE*60
DAY = HOUR*24

'''
This grader script is the actual running process for grading the assignments.

It loads the course setting from config.json stored in the same folder.
This config contains all the information about when to start grading and stop grading
the assignments. The name of the master files etc. Look at the file, its very simple
'''

    

with open("configGrader.json","r") as f:
    conf = json.load(f)

course = Course(API_URL=conf['API_URL'],API_KEY=conf['API_KEY'],COURSE_ID=conf['course'])


for assignment_conf in conf['Assignments']:
    assnames = [assignment.attributes['name'] for assignment in course.assignments]
    assert assignment_conf['name'] in assnames
    
    assignment = [assignment for assignment in course.assignments if assignment.attributes['name'] == assignment_conf['name']][0]
    
    assert assignment.attributes['name'] == assignment_conf['name'], "assignment name mismatch"

    final_minute_for_start_date = "-00:01" 
    final_minute_for_end_date = "-23:59" 
    date_format = "%Y-%m-%d-%H:%M"
    assignment_start_date = datetime.strptime(assignment_conf['start_date']+final_minute_for_start_date,date_format)
    assignment_end_date = datetime.strptime(assignment_conf['end_date']+final_minute_for_end_date,date_format) 

    while (datetime.now() < assignment_start_date):
        print("Waiting for %s to start, which is %s" % (assignment_conf['name'],assignment_start_date))
        time.sleep(DAY)
    if (datetime.now() > assignment_start_date):
        print("Grading window for %s has started" % assignment_conf['name'])
        auto = Autograder.makeAutoGrader(course,assignment,assignment_conf,conf,sharp=True)
        while (datetime.now() < assignment_end_date):
            auto.grade()
            print("Taking a 30 minute break")
            time.sleep(30*MINUTE)
            pass
        print("Grading window for %s has ended" % assignment_conf['name'])
    else:
        print("Grading window for %s is not active" % assignment_conf['name'])
