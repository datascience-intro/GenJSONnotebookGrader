#from NotebookGrader import initConfigFiles
from .dbcRestWrapper import *
from .AutoGrader import *
from zipfile import ZipFile
import os
import shutil

class DBAutoGrader(Autograder):
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
        # write to disk as source file (.scala, .r, etc)
        source_file_extension = studentSubmissionFileName.split(".")[-1]

        with open('Response/Response_%d_%d.%s' % (student_id,submission_attempt,source_file_extension), mode='w') as f:
            json.dump(response_notebook, f)

        # zip to dbc
        with ZipFile('Response/Response_%d_%d.dbc' % (student_id,submission_attempt), 'w') as zipObj:
            zipObj.write('Response/Response_%d_%d.%s' % (student_id,submission_attempt,source_file_extension) \
                        ,'Response_%d_%d.%s' % (student_id,submission_attempt,source_file_extension)) #<< Finally got it as .dbc !
        
        # remove source file, so only dbc with source file inside is left.
        os.remove('Response/Response_%d_%d.%s' % (student_id,submission_attempt,source_file_extension))
    


    def extractStudentAndMasterFiles(self,studentSubmissionFileName,studentSubmissionFilePath,student_id,submission):
        """
        Extracts the student and master files from the notebook.
        """
        with ZipFile(studentSubmissionFileName, 'r') as zipObj: #<< full path including file name
            # Extract all the contents of zip file
            zipObj.extractall(studentSubmissionFilePath) #<< path to dir that stores the file, w/o file name
            # Get the extension of the source file inside .dbc << it can be .scala, .r, etc.
            source_file_name = [file_name for file_name in zipObj.namelist() if file_name.split(".")[-1] != "mf"][0] # only file name, w/o path
            print("source_file_name: ",source_file_name)
            source_file_extension = source_file_name.split(".")[-1]
        
        # source file name inside dbc and the file name of dbc itself might have different names
        # so we rename the source file name inside to be the same as the dbc file name.
        old_name = studentSubmissionFilePath+"/"+source_file_name
        new_name = studentSubmissionFilePath+"/"+str(student_id)+"_"+str(submission['attempt'])+"."+source_file_extension
        os.rename(old_name, new_name)                                    
        
        studentSubmissionFileName = new_name # << .scala, .r, etc, but not .dbc ! << full path

        # extract master file
        # self.master_nb_filename
        # eg. Master/Assignment_1_problem_TEST.dbc

        master_nb_file_path = "/".join(self.master_nb_filename.split("/")[0:-1]) # only path, w/o file name
        master_nb_only_file_name = self.master_nb_filename.split("/")[-1].split(".")[0] # only file name, wo ext
        with ZipFile(self.master_nb_filename, 'r') as zipObj: #<< full path including file name
            # Extract all the contents of zip file
            zipObj.extractall(master_nb_file_path) #<< path to dir that stores the file, w/o file name
            # Get the extension of the source file inside .dbc << it can be .scala, .r, etc.
            source_file_name = [file_name for file_name in zipObj.namelist() if file_name.split(".")[-1] != "mf"][0] # only file name, w/o path
            source_file_extension = source_file_name.split(".")[-1]
        
        # source file name inside dbc and the file name of dbc itself might have different names
        # so we rename the source file name inside to be the same as the dbc file name.
        old_name = master_nb_file_path+"/"+source_file_name
        new_name = master_nb_file_path+"/"+master_nb_only_file_name+"."+source_file_extension
        os.rename(old_name, new_name)   
                            
        return new_name,studentSubmissionFileName
    
    def StringToNotebook(self,nb_string,as_version=4):
        return json.loads(nb_string)

    def addSummary(self,finalGradeDict,graded_ass_nb,graded_nb):
        #cannot do the following in AssignmentNotebook/extractResult so do it here instead 
        totScore = 0
        posScore = 0
        for cell in graded_nb['commands']:
            if 'lx_problem_cell_type' in cell['metadata']:
                if cell['metadata']['lx_problem_cell_type'] == 'TEST':
                    posScore += int(cell['metadata']['lx_problem_points'])
            #if 'lx_python_score_in_total' in cell['metadata'] or 'lx_scala_score_in_total' in cell['metadata']:
            if cell['results'] != None:
                if "data" in cell['results']:
                    if isinstance(cell['results']['data'], list): # if data is list << actually for python
                        if len(cell['results']['data']) > 0: 
                            if "data" in cell['results']['data'][0]:
                                s = cell['results']['data'][0]['data'] # text output

                                sSplitByNewLines = s.split('\n')
                                ls = ''.join(sSplitByNewLines[0:]) # s --> ls (remove \n)

                                # for whatever lanaguage (scala, r, python, etc), the score summary in the last test cell must stricly be in this format !
                                #matchObj = re.match(r"^.*points you have scored in total for all Problems in [A-Za-z]+ is\s+(\d+)\s+out of\s+(\d+).*$", ls, flags=re.M | re.DOTALL | re.UNICODE)
                                matchObj = re.match(r"^.*points you have scored for this problem is\s+(\d+)\s+out of\s+(\d+).*$", ls, flags=re.M | re.DOTALL | re.UNICODE)
                                if matchObj:
                                    
                                    totScore += int(matchObj.group(1))
                                    #posScore += int(matchObj.group(2))
                                
                    elif(isinstance(cell['results']['data'], str)): # if data is string << actually for scala
                        s = cell['results']['data'] # text output

                        sSplitByNewLines = s.split('\n')
                        ls = ''.join(sSplitByNewLines[0:]) # s --> ls (remove \n)

                        # for whatever lanaguage (scala, r, python, etc), the score summary in the last test cell must stricly be in this format !
                        matchObj = re.match(r"^.*points you have scored for this problem is\s+(\d+)\s+out of\s+(\d+).*$", ls, flags=re.M | re.DOTALL | re.UNICODE)
                        #matchObj = re.match(r"^.*points you have scored in total for all Problems in [A-Za-z]+ is\s+(\d+)\s+out of\s+(\d+).*$", ls, flags=re.M | re.DOTALL | re.UNICODE)
                        if matchObj:
                            totScore += int(matchObj.group(1))
                            #posScore += int(matchObj.group(2))
        
            finalGradeDict['lx_problem_total_scored_points']=str(totScore)
            finalGradeDict['lx_problem_total_possible_points']=str(posScore)
        
        final_graded_nb = graded_ass_nb.notebook

        for cell in final_graded_nb['commands']:
            matchObj = re.match(r"^.*points you have scored in total for this entire set of Problems is XXXXXXXXXX out of YYYYYYYYYY.*$", cell['command'], flags=re.M | re.DOTALL | re.UNICODE)
            if matchObj:
                md = '''The number of points you have scored in total for this entire set of Problems is {} out of {}.'''.format(finalGradeDict['lx_problem_total_scored_points'], finalGradeDict['lx_problem_total_possible_points'])
                cell['command'] = '''%md\n'''+md
                finalGradeDict['text_response'] = finalGradeDict['text_response']+"\n"+md


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

            
            result = {"stdout":"","timeout":False,"oom_killed":False,"unknown_error":False,"stderr":"","exit_code":0,"duration":0}
            job_conf, grader_conf = initConfigFiles(assName)
    
            #directories in you databricks workspace
            dbc_workspace_dir = grader_conf["dbc_workspace_dir"]
            dbc_grading_dir = dbc_workspace_dir + "/Grading/" + assName 
            dbc_HTML_dir = dbc_grading_dir + "/Graded_HTML"
            dbc_GradedWoTest_dir = dbc_grading_dir + "/Graded_wo_TEST"

               
            # directories on your local machine
            result_dir_dbc = f"./Grading/Graded/{assName}/dbc_result_dir"
            result_dir_html =f"./Grading/Graded/{assName}/html_result_dir" 


            import os
            current_dir = os.getcwd() 

            source_file_name = "Graded_Notebook_for_"+assName # << now_grading.scala or now_grading.python to be graded
            source_file_extension = notebook['language']

            target_filename_source = current_dir+"/"+source_file_name+"."+source_file_extension 
            #same but with dbc instead of sfe
            target_filename_dbc = current_dir+"/"+source_file_name+".dbc"
            target_filename_html = current_dir+"/"+source_file_name+".html"

            # write as source file (.scala, .py, etc)
            with open(target_filename_source, mode='w') as f:
                json.dump(notebook, f)

            with ZipFile(target_filename_dbc, 'w') as zipObj:
                zipObj.write(target_filename_source, source_file_name+"."+source_file_extension)
            
            os.remove(target_filename_source)
            pure_name = "Graded_Notebook_for_" + assName
            name = pure_name + ".dbc"

            api_client = ApiClient(
                host  = get_config().host,
                token = get_config().token
                )
            workspace = WorkspaceApi(api_client)
            try:
                workspace.delete(dbc_grading_dir,True)
            except OSError as e:
                print(e)

            #create new folders

            workspace.mkdirs(grader_conf["dbc_workspace_dir"] + "/Grading/" + assName)
            workspace.mkdirs(grader_conf["dbc_workspace_dir"] + "/Grading/" + assName + "/Graded_HTML")
            workspace.mkdirs(grader_conf["dbc_workspace_dir"] + "/Grading/" + assName + "/Graded_wo_TEST")
            
            try:
                shutil.rmtree(f"./Grading/Graded/{assName}")
                
            except:
                print("dbc-folder-remove not needed")
            os.makedirs(f"./Grading/Graded/{assName}/dbc_result_dir",exist_ok=True)
            os.makedirs(f"./Grading/Graded/{assName}/html_result_dir",exist_ok=True)
            startCluster(api_client,grader_conf['dbc_cluster_id'])
            
            #source_file_extension = "SCALA" #Notebook[language].toUpper()
            target_path_dbc = job_conf["notebook_task"]["notebook_path"]

            source_path = "./Graded_Notebook_for_" + assName + ".dbc"
            
            #"/Users/oskar.asbrink.9367@student.uu.se/Grading/TEST_ASSIGNMENT_1/Graded_Notebook_for_TEST_ASSIGNMENT_1.dbc"
            workspace.import_workspace(source_path,target_path_dbc,source_file_extension.upper(),"DBC",False)
            
            
            id = createAndRunJob(api_client,job_conf)

            with ZipFile(source_path, mode='r') as zipObj:
                zipObj.extractall(os.getcwd())
                source_file_name = [file_name for file_name in zipObj.namelist() if file_name.split(".")[-1] != "mf"][0]



            req = requests.get(f"https://uppsalauni-scadamale-ds-projects.cloud.databricks.com/api/2.0/jobs/runs/export?run_id={id}")

            with open("run_res.txt",'w') as f:
                f.write(json.dumps(req.json()))          
            extract_content("run_res.txt",result_dir_html)
            

            workspace.import_workspace(result_dir_html + "/" + pure_name + ".html",dbc_HTML_dir + "/" + pure_name,source_file_extension,"HTML",False)
            workspace.export_workspace(dbc_HTML_dir + "/" + pure_name , result_dir_dbc + "/" + pure_name,"DBC",True)

        
            with ZipFile(result_dir_dbc + "/" + pure_name, mode='r') as zipObj:
                zipObj.extractall(result_dir_dbc)

            
            result_path = "./Grading/Graded/"+assName+"/dbc_result_dir/"+source_file_name
            with open(result_path, mode="r") as f:
                result['stdout'] = json.dumps(json.loads(f.read())) # as a json string << will be converted to json dict later

            os.remove(target_filename_dbc)
            os.remove(result_path)
            os.remove(source_file_name)
            os.remove("run_res.txt")
            return result
            
            
        return None

