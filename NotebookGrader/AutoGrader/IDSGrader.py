from .AutoGrader import *
#from dbcRestWrapper import *
import shutil

class IDSAutoGrader(Autograder):


    def __init__(self, course, assignment, master_nb_filename,sharp=False):
        '''
        Creates an Autograder object

        Keyword arguments
        course -- a Course object
        assignment -- an Assignment object that will be graded
        master_nb_filename -- The filename of the notebook that contains the tests
        sharp -- If the grading should be sharp, meaning that it should upload to Studium.
        '''
        #self.course = course
        #self.assignment = assignment
        #self.assignment_id = self.assignment.attributes['id']
        #self.master_nb_filename = master_nb_filename
        #self.sharp = sharp
        #self.submissions = None
        super().__init__(course, assignment, master_nb_filename,sharp)

    def writeResponseFile(self,response_notebook,student_id,submission_attempt,studentSubmissionFileName):
        with open('Response/Response_%d_%d.ipynb' % (student_id,submission_attempt),mode='w') as f:
            nbformat.write(response_notebook,f)
        

    def extractStudentAndMasterFiles(self,studentSubmissionFileName,studentSubmissionFilePath,student_id,submission):
        """
        This method is not needed for this platform
        Extracts the student and master files from the notebook.
        """
        return self.master_nb_filename,studentSubmissionFileName

    def StringToNotebook(self,nb_string,as_version=4):
        return nbformat.reads(nb_string, as_version)


    def addSummary(self,finalGradeDict,graded_ass_nb,graded_nb):
        final_graded_nb = graded_ass_nb.notebook
        md = '''The number of points you have scored in total for this entire set of Problems is {} out of {}.'''.format(finalGradeDict['lx_problem_total_scored_points'], finalGradeDict['lx_problem_total_possible_points'])
        newCell = nbformat.v4.new_markdown_cell(md)
        final_graded_nb['cells'].append(newCell)
        finalGradeDict['text_response'] = finalGradeDict['text_response']+md
        return finalGradeDict,final_graded_nb

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
        if notebook: # pass notebook as json dict for grading     
        
            
            import epicbox
            epicbox.config.DOCKER_WORKDIR = '/home/sage/'
            
            epicbox.configure(
                profiles=[
                    epicbox.Profile('python', 'sds-sagemath-autograde:latest',user='sage')
                ]
            )

            
            import os
            data_dir = os.listdir('data')
            files = []
            
            for filename in data_dir:
                with open('data/'+filename,'rb') as f:
                    files.append({'name': filename, 'content': f.read()})
            make_data_dir_command = 'mkdir data;'
            move_command = ''.join(["mv %s data/;" % x['name'] for x in files])
            files.append({'name': 'main.ipynb', 'content': bytes(notebook,encoding='utf-8')})
            
            # These limits are basically heuristic, and my idea is to make this an option somehow
            # Remember when setting these values is that Epicbox is sandboxing your code and not
            # allowing any swap at all, thus 1024 is the total memory used
            # also note that due to not being able to swap seems to slow the code down a bit
            # and cputime needs to be fairly generous
            
            limits = {'cputime':200,'memory': 1024}
            
            # In the nbconvert statement we are using the timeout and set to 600
            # I am not sure what implication that number actually has, because it is not 1-1 with
            # actual time. But the higher the more timout at least.
            
            command = 'true;' + make_data_dir_command + move_command + 'jupyter nbconvert --to notebook --ExecutePreprocessor.kernel_name=sagemath --ExecutePreprocessor.timeout=600 --execute --allow-errors --stdout main.ipynb'
            result = epicbox.run('python', command, files=files, limits=limits)#,workdir=workdir)
            result['unknown_error'] = False #<< This is only used for databricks.

            return result

        return None # If no notebook, return none.



