import urllib.request
import nbformat
from NotebookGrader.AssignmentNotebook.AssignmentNotebook import AssignmentNotebook
import os
import json
from zipfile import ZipFile
import re
import subprocess


class Autograder:
    def __init__(self, course, assignment, master_nb_filename,sharp=False, runtime_config=None):
        '''
        Creates an Autograder object

        Keyword arguments
        course -- a Course object
        assignment -- an Assignment object that will be graded
        master_nb_filename -- The filename of the notebook that contains the tests
        sharp -- If the grading should be sharp, meaning that it should upload to Studium.
        '''
        self.course = course
        self.assignment = assignment
        self.assignment_id = self.assignment.attributes['id']
        self.master_nb_filename = master_nb_filename
        self.sharp = sharp
        self.submissions = None
        self.runtime_config = runtime_config or {}
        #self.nbserver <- databricks, zeppelin, jupyter(incl sage)
    @staticmethod
    def makeAutoGrader(course,assignment,assignment_conf,conf=None,sharp=False):
        #factory function to give correct autograder object
        file_ext = assignment_conf["master_filename"].split(".")[-1]
        if file_ext == "ipynb":
            from .IDSGrader import IDSAutoGrader
            return IDSAutoGrader(
                course,
                assignment,
                assignment_conf['master_filename'],
                sharp,
                runtime_config=conf,
            )
        elif file_ext == "dbc":
            from .DBGrader import DBAutoGrader
            return DBAutoGrader(course,assignment,assignment_conf['master_filename'],sharp,conf['dbc_workspace_dir'])
        else:
            raise Exception("Unknown notebook file extension")
    def _getSubmissions(self): #<< no need to change
        '''
            Downloads all submissions for the assignment
        '''

        self.submissions = self.course.getAssignmentSubmissions(self.assignment_id)

    def _getSubmissionsStats(self):
        '''
            Downloads all submission statistics (can be extended)

            Returns:
            listStatsDict -- A list of stats dictionaries
        '''
        self._getSubmissions()
        listStatsDict = []
        for submission in self.submissions:
            statsDict = {}
            if (submission['grade'] != None):
                statsDict['attempts'] = int(submission['attempt'])
                statsDict['grade'] = int(submission['grade'])
                listStatsDict.append(statsDict)
        return listStatsDict

    def _uploadFile(self,student_id,attemptnr,inputStream=None,filename=None):
        '''
            Uploads a file as a comment on the submission
            will be stored on Studium with attemptnr appended to the end of the name

            Keyword arguments:
            inputStream -- optional in-memory file object to upload instead of a file in Response/
            filename -- optional filename to use when inputStream is supplied

            Returns:
            id -- the file_id that Studium assigns to this uploaded file, important to store
        '''
        if not self.sharp:
            return None
        filtered_submissions = [submission for submission in self.submissions if submission['user_id'] == student_id]
        submission = filtered_submissions[0] # submission with a correct student id

        import requests
        user_id = submission['user_id']
        user_name = self.course.get_user(user_id)['name'].replace(" ","_")
        pure_file_extension = self.master_nb_filename.split(".")[-1] # dbc, ipynb
        if pure_file_extension == "dbc":
            file_extension="html"
            content_type = "text/html"
        else:
            file_extension = pure_file_extension
            content_type = "application/x-ipynb+json" if file_extension == "ipynb" else file_extension
        if filename is None:
            filename = "Response_%d_%d.%s" % (user_id,attemptnr,file_extension)
        re_str = (self.course.base_req_str
            +  "/assignments/"+ str(self.assignment_id)
            + "/submissions/" +str(user_id)
            + "/comments/files"
            + "?name=%s" % (filename) # Done
            + "&content_type=%s" % (content_type) # Done
            +"&access_token=" + self.course.API_KEY)

        response = requests.post(re_str)

        try:
            upload_info = response.json()
            url = upload_info['upload_url']
            upload_params = upload_info.get('upload_params', {})
            if inputStream is not None:
                if hasattr(inputStream, 'seek'):
                    inputStream.seek(0)
                files = {'file': (filename, inputStream, content_type)}
                r = requests.post(url, data=upload_params, files=files)
            else:
                response_filename = 'Response/Response_%d_%d.%s' % (user_id,attemptnr,file_extension)
                with open(response_filename, 'rb') as response_file:
                    files = {'file': (filename, response_file, content_type)}
                    r = requests.post(url, data=upload_params, files=files)

            print("action=uploaded-feedback-file")
            if self.sharp:

                if pure_file_extension != "ipynb":
                    
                    from NotebookGrader import upload_feedback_to_workspace
                    upload_feedback_to_workspace('Response/Response_%d_%d.%s' % (user_id,attemptnr,file_extension),user_name,user_id,attemptnr)

        except Exception as error:
            print(f"action=feedback-file-error error={type(error).__name__}")
            return None
        
        
        return r.json()['id'] #<< file_id

    @staticmethod
    def _summaryComment(grade, *, return_notebook_attached):
        if return_notebook_attached:
            return (
                f"Autograding complete. Score: {grade}. "
                "See the attached return notebook for detailed feedback."
            )
        return (
            f"Autograding complete. Score: {grade}. "
            "The return notebook could not be attached; contact course staff "
            "for detailed feedback."
        )

    def _uploadSubmissionGrade(self,submission,grade,comment,inputStream=None):
        '''
            Uploads a grade and a comment for a submission up on the Studium website

            Keywords arguments:
            submission -- a submission
            grade -- integer representing the grade
            comment -- detailed feedback stored in the return notebook; it is not
                copied into the Studium text comment
            inputStream -- optional in-memory response file to attach to the submission comment
        '''
        user_id = submission['user_id']
        attempt = submission.get('attempt', '?')
        assignment_name = self.assignment.attributes.get('name', '<unknown>')

        if not self.sharp:
            print(
                "assignment=%r attempt=%s score=%s action=dry-run-no-upload"
                % (assignment_name, attempt, grade)
            )
            return None

        import requests

        file_id = self._uploadFile(
            user_id,
            submission['attempt'],
            inputStream=inputStream,
        )
        summary_comment = self._summaryComment(
            grade,
            return_notebook_attached=file_id is not None,
        )

        if (file_id != None): # comment, grade, and file to be uploaded as feedback << ok
            re_str = (self.course.base_req_str
                        + "/assignments/"+ str(self.assignment_id)
                        + "/submissions/" +str(user_id)
                        + "?submission[posted_grade]="+str(grade)
                        + "&comment[file_ids]=%d" % file_id
                        + "&comment[attempt]=%d" % submission['attempt']
                        + "&comment[text_comment]=" + summary_comment
                        + "&access_token=" + self.course.API_KEY)
        else: # comment and grade to be uploaded (no file to be uploaded) as feedback << ok
            re_str = (self.course.base_req_str
                        + "/assignments/"+ str(self.assignment_id)
                        + "/submissions/" +str(user_id)
                        + "?submission[posted_grade]="+str(grade)
                        + "&comment[attempt]=%d" % submission['attempt']
                        + "&comment[text_comment]=" + summary_comment
                        + "&access_token=" + self.course.API_KEY)

        response = requests.put(re_str)
        print(
            "assignment=%r attempt=%s score=%s action=uploaded"
            % (assignment_name, attempt, grade)
        )
        return response

    def _uploadSubmissionComment(self,user_id,comment,force=False):
        '''
            Uploads a submission comment to a certain user, useful when manually checking assignments.

            Keywords arguments:
            user_id -- an integer representing the student id
            comment -- the content to upload
            force -- if this should be forcefully put up, in general you have to have force=True but can be kept as false
            to make sure you are sending the right thing.
        '''
        if not self.sharp:
            print("assignment=%r action=dry-run-no-comment" % self.assignment.attributes.get('name', '<unknown>'))
            return None
        import requests

        re_str = self.course.base_req_str +  "/assignments/"+ str(self.assignment_id)+ "/submissions/" +str(user_id) +  "?comment[text_comment]=" + comment[-2000:] + "&access_token=" + self.course.API_KEY
        return requests.put(re_str)

    def _gradeSubmission(self,submission,force=False, only_prepare=False):
        '''
            Runs the autograding for the submission and returns the grade and comment

            Keyword arguments:
            submission -- the submission
            force -- used to regrade an assignment

            Returns:
            grade -- the grade
            comment -- the comment
            update_grade -- if the grade of this submission should be updated, used to decide if
            we should upload the new grade to the Studium platform. Will be set to true if force=True
            and there actually is a submission.
        '''
        student_id = submission['user_id']
        comment = ""
        grade = 0
        update_grade = False


        if ((submission['workflow_state'] == 'unsubmitted')):

            pass
        else:
            if ((submission['grade'] == None) | (submission['grade_matches_current_submission'] == False) | (force)):
                if (submission['missing'] == False): # Just testing to see that the submission actually exists
                    update_grade=True
                    if ('attachments' in submission):
                        self.course.get_user(student_id)

                        # Download attachment
                        attachments = submission['attachments']
                        if (len(attachments) == 1):
                            print(
                                "assignment=%r attempt=%s action=download"
                                % (self.assignment.attributes.get('name', '<unknown>'), submission.get('attempt', '?'))
                            )

                            file_extension = attachments[0]['filename'].split(".")[-1] # <<< ext here can be .dbc or .ipynb
                            studentSubmissionFileName = "StudentSubmission/"+str(student_id)+"_"+str(submission['attempt'])+"."+file_extension # << .dbc, .ipynb
                            studentSubmissionFilePath = "/".join(studentSubmissionFileName.split("/")[0:-1])
                            urllib.request.urlretrieve(attachments[0]['url'],studentSubmissionFileName) # << .dbc, .ipynb

                            masterNotebookFileName = self.master_nb_filename

                            masterNotebookFileName,studentSubmissionFileName = self.extractStudentAndMasterFiles(studentSubmissionFileName,studentSubmissionFilePath,student_id,submission)
                            try:
                                if (only_prepare):
                                    grade = 0
                                    comment = ""
                                    self.prepareNotebookForGrading(studentSubmissionFileName,masterNotebookFileName,student_id) # <<< .ipynb, .scala, .r, etc (not dbc)
                                else:
                                    gradeDict = self.safeGradeNotebook(studentSubmissionFileName,masterNotebookFileName,student_id, assName = self.assignment.attributes['name']) # <<< .ipynb, .scala, .r, etc (not dbc)
                                    grade = gradeDict['lx_problem_total_scored_points']
                                    comment = gradeDict['text_response'].replace('#','')
                                    #writeResponseFile
                                    if (gradeDict['Response_Notebook'] != ''): #<< json dict << check if it is dbc (zip + remove) or ipynb
                                        self.writeResponseFile(gradeDict['Response_Notebook'],student_id,submission['attempt'],studentSubmissionFileName)

                                print(
                                    "assignment=%r attempt=%s score=%s action=graded"
                                    % (self.assignment.attributes.get('name', '<unknown>'), submission.get('attempt', '?'), grade)
                                )
                            except Exception as e:
                                comment = type(e).__name__
                                print(
                                    "assignment=%r attempt=%s action=grading-error error=%s"
                                    % (self.assignment.attributes.get('name', '<unknown>'), submission.get('attempt', '?'), type(e).__name__)
                                )
                        else:
                            comment = 'You should only have one file in the submission'
                else:
                    pass

        return grade, comment, update_grade

    def getStudentSubmission(self,student_id,student_name=None):
        '''
            Downloads the students submission into a locally stored notebook file
            Keyword arguments:
            student_id -- integer representing the identity of the student

            Returns:
            file_name -- the filename of the student notebook
        '''
        self._getSubmissions()
        filtered_submissions = [submission for submission in self.submissions if submission['user_id'] == student_id]
        assert len(filtered_submissions) == 1, "Student does not exist"
        submission = filtered_submissions[0]
        if (type(student_name) == str):
            file_name = "StudentSubmission/"+str(student_id)+"_"+student_name+".ipynb"
        else:
            file_name = "StudentSubmission/"+str(student_id)+".ipynb"
        attachments = submission['attachments']
        urllib.request.urlretrieve(attachments[0]['url'],file_name)
        return file_name


    def grade(self,force=False): # >> nothing changed
        '''
            Grades all ungraded submissions
        '''
        self._getSubmissions()
        for submission in self.submissions:
            self.currentSubmission = submission
            grade, comment,update_grade = self._gradeSubmission(submission,force)
            if (update_grade):
                self._uploadSubmissionGrade(submission,grade,comment)
            #upload to databricks
        print("action=grading-round-complete")

    def gradeControlledSubmission(self, student_id=None):
        """Grade at most one submitted attempt, uploading only in sharp mode."""
        self._getSubmissions()
        candidates = [
            submission
            for submission in self.submissions
            if submission.get('workflow_state') != 'unsubmitted'
            and not submission.get('missing', False)
            and len(submission.get('attachments', [])) == 1
        ]
        if student_id is not None:
            candidates = [
                submission for submission in candidates
                if submission.get('user_id') == student_id
            ]
        if not candidates:
            return None
        submission = candidates[0]
        grade, comment, update_grade = self._gradeSubmission(submission, force=True)
        action = "graded-no-upload"
        if update_grade and self.sharp:
            self._uploadSubmissionGrade(submission, grade, comment)
            action = "uploaded"
        return {
            "attempt": submission.get('attempt'),
            "score": grade,
            "action": action,
            "feedback": comment,
        }


    def gradeStudentSubmission(self,student_id,only_prepare=False):
        '''
            Forcefully grades the submission for student, i.e. even if last submission already graded it will
            be graded again

            Keyword arguments:
            student_id -- integer representing the identity of the student
        '''
        self._getSubmissions()
        filtered_submissions = [submission for submission in self.submissions if submission['user_id'] == student_id]
        assert len(filtered_submissions) == 1, "Student does not exist"
        submission = filtered_submissions[0]
        grade, comment,update_grade = self._gradeSubmission(submission,force=True,only_prepare=only_prepare)
        if (update_grade & (not only_prepare)):
            return self._uploadSubmissionGrade(submission,grade,comment)
        print("action=student-grading-complete")


    def gradeStudentsWithGrade(self,grade,only_prepare=False):
        '''
            Forcefully grades all submissions with grade==grade

            Keyword arguments:
            grade -- integer representing the grade

            Returns:
            a list of the submissions with grade==grade
        '''
        self._getSubmissions()
        filtered_submissions = [submission for submission in self.submissions if submission['grade'] == str(grade)]

        for submission in filtered_submissions:
            grade, comment,update_grade = self._gradeSubmission(submission,force=True,only_prepare = only_prepare)
            if (update_grade & (not only_prepare)):
                self._uploadSubmissionGrade(submission,grade,comment)

        return [submission['user_id'] for submission in filtered_submissions]

    def addSummary(self,finalGradeDict,graded_ass_nb,graded_nb):
        NotImplementedError("AutoGrader addSummary is implemented in subclasses.")


    def safeRunNotebook(self,notebook = None, assName=""):

        '''
            Takes a notebook in string format and spins up a sandboxed docker image that will run the grading
            >> notebook as JSON string (s: unicode). Use "reads" to convert it to NotebookNode, and use "write" to save NotebookNode as .ipynb file

            Keyword arguments:
            notebook -- a jupyter notebook loaded as string, using for instance nbformat.writes

            Returns:
            result -- A result dict that contains the following keys:
                stdout -- stdout
                stderr -- stderr >> not supported by whales
                exit_code -- exit code >> not supported by whales
                duration -- the time in seconds this was run >> not supported by whales
                timeout -- False or True if the notebook timed out
                oom_killed -- False or True depending on if the notebook used all memory
                unknown_error -- False or True, True if error is unknown, but not by oom or timeout
        '''
        raise NotImplementedError("safeRunNotebook is implemented in subclasses.")

    def prepareNotebookForGrading(self,student_nb_filename,master_soln_nb_filename,student_id = 0,student_name = None):
        '''
            Takes a student notebook, inserts the tests from the master notebook.
            Stores the file locally named 'student_solution_with_tests' + str(student_id) + '.ipynb'

            Keyword arguments:
            student_nb_filename -- the filename of the student notebook << eg. "StudentSubmission/<Student_ID>_<attempt>.ipynb" .scala, .r, etc. but not .dbc ! If dbc, it has to be zipped !
            master_soln_nb_filename -- the filename of the notebook that contains the tests << eg. "Master/Assignment_XXX_problem_TEST.ipynb" .scala, .r, etc. but not .dbc ! << If dbc, it has to be zipped ! << filename loaded from config.json
            student_id -- integer representing the student id

            Returns:
            notebook -- the notebook with all tests appended
        '''

        student_nb = AssignmentNotebook.createAssignmentNotebook(nb_filename = student_nb_filename,extension = master_soln_nb_filename.split(".")[-1]) # IDSAss has supported .scala,.r,. ipynb, etc. << _gradeSubmission() that calls this method still needs modification to handle nb type (ipynb, dbc) << "StudentSubmission/<Student_ID>_<attempt>.ipynb" << full path
        master_soln_nb = AssignmentNotebook.createAssignmentNotebook(nb_filename = master_soln_nb_filename,extension = master_soln_nb_filename.split(".")[-1]) # << IDSAss has supported .scala,.r,. ipynb, etc. << _gradeSubmission() that calls this method still needs modification to handle nb type (ipynb, dbc) << "Master/Assignment_XXX_problem_TEST.ipynb"
        student_solution_with_tests = student_nb + master_soln_nb # << object AssignmentNotebook (not IDSAssignmentNotebook !)
        file_extension = student_nb_filename.split(".")[-1] # ipynb, scala, r << not .dbc !!! << if dbc, it has to be zipped !
        if (student_name != None):
            student_solution_with_tests.to_nb('SolutionWTest/student_solution_with_tests_%s_%s.%s'% (str(student_id),student_name,file_extension)) # << we will finally get a notebook as .ipynb or .dbc !
        else:
            student_solution_with_tests.to_nb('SolutionWTest/student_solution_with_tests_'+ str(student_id) +"."+ file_extension) # << we will finally get a notebook as .ipynb or .dbc !
        return student_solution_with_tests # << object AssignmentNotebook (not IDSAssignmentNotebook !)

    def safeGradeNotebook(self,student_nb_filename,master_soln_nb_filename,student_id = 0,assName=""):
        '''
            Takes a student notebook, inserts the tests from the master notebook and runs the code, and
            returns the result.

            Keyword arguments:
            student_nb_filename -- the filename of the student notebook << eg. "StudentSubmission/<Student_ID>_<attempt>.ipynb" .scala, .r, etc. but not .dbc ! If dbc, it has to be zipped !
            master_soln_nb_filename -- the filename of the notebook that contains the tests << eg. "Master/Assignment_XXX_problem_TEST.ipynb" .scala, .r, etc. but not .dbc ! << If dbc, it has to be zipped ! << filename loaded from config.json
            student_id -- integer representing the student id

            Returns:
            finalGradeDict -- A dictionary representing the result of the notebook grading, has the following keys,
                lx_problem_total_scored_points -- how many points scored
                lx_problem_total_possible_points -- how many points possible
                text_response -- the output of the notebook
                Response_Notebook -- The run notebook
        '''

        finalGradeDict = {'lx_problem_total_scored_points':0,
                        'lx_problem_total_possible_points':0,
                        'text_response':'',
                        'Response_Notebook':''}

        # student_withInjectedTESTs_nb has a type of AssignmentNotebook
        # both filename can only be ipynb or source file (.scala, .r, etc unzipped from dbc) << file handled from _gradeSubmission()
        student_withInjectedTESTs_nb = self.prepareNotebookForGrading(student_nb_filename,master_soln_nb_filename,student_id)
        #print(student_withInjectedTESTs_nb.nb_as_json(notebook_language="ipynb"))
        file_extension = student_nb_filename.split(".")[-1]

        content = student_withInjectedTESTs_nb.nb_as_json(notebook_language = file_extension)
        #print(content)
        #if file_extension != "ipynb": # scala, r, etc.
        result = self.safeRunNotebook(content, assName=assName) # pass json dict of *dbc* (as a source file) into safeRunNotebook <<<<<<<<<<<<<<<<<<<<<<<<<
        #print(result)

        #assert result['timeout']==False , 'Your notebook timed out, try to optimize your code'
        errorComment = ""
        if result['timeout']:
            errorComment = 'Your notebook timed out, try to optimize your code'
        elif result['oom_killed']:
            errorComment = 'Your notebook used too much memory, try to optimize your code'
        elif result['unknown_error']:
            errorComment = 'Your notebook has an unknown error (but not about timeout and oom), please check'

        try:
            #if file_extension != "ipynb": # scala, r, etc.
            graded_nb = self.StringToNotebook(result['stdout']) # load json string into json dict

        except:
            # We need this, because if something crashes that is not because of
            # timeout or oom_killed then the stdout will not be a notebook it will
            # be an error message, so we say unknown error and tell the students to alert this to us
            # we can then "manually" grade that file.
            if (errorComment == ""):
                errorComment = 'Your notebook has an unknown error, please check. The most likely culprit is that you have an infinite loop, a bug or simply that your code took too long to run. Please alert the course staff if you think this is an error.'
            graded_nb = None

        if (graded_nb):
            graded_ass_nb = AssignmentNotebook.createAssignmentNotebook(notebook=graded_nb,extension=file_extension) # AssignmentNotebook object << ok !
            finalGradeDict, stdOutString = graded_ass_nb.extractResult() # Done
            finalGradeDict.update({'text_response': stdOutString}) # Done
            #we can add this in assignmentnotebook class probably
            finalGradeDict,final_graded_nb = self.addSummary(finalGradeDict,graded_ass_nb,graded_nb) # Done)
            # cannot do the following in AssignmentNotebook/extractResult so do it here instead

            # finalGradeDict.update({'Response_Notebook': graded_ass_nb.notebook}) # json dict << Done
            finalGradeDict.update({'Response_Notebook': final_graded_nb}) # json dict << Done
        else:
            finalGradeDict.update({'text_response': errorComment})

        return finalGradeDict

    def writeResponseFile(self,response_notebook,student_id,submission_attempt,studentSubmissionFileName):
        raise NotImplementedError("AutoGrader writeResponseFile is implemented in subclasses.")
