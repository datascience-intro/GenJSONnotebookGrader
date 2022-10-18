from ntpath import join
from hashlib import new
from distutils.command.build_scripts import first_line_re
from curses import raw
import nbformat
import re
import os 
import json 
from zipfile import ZipFile 

class CourseNotebook:
    """
    Represents a course notebooks


    Attributes
    ----------
    courseDetails : CourseDetails
    header : str
        the header string, to be put as the first cell when outputting
        as a notebook
    assignmentNumbers : [int]
        If there are assignment problems in this notebook, the assignment
        number/numbers will be stored here.
    assignmentCells : [nbformat cell]
        these are all the assignment related cells contained in this notebook
    notebook : nbformat.NotebookNode
        the raw notebook, if loaded from file
    nb_filename : str
        the filename of the raw notebook

    Methods
    -------
    getAssignments(assignmentNumber=0)
        returns the problems found in this courseNotebook related to
        assignmentNumber

    toLectureNotebook(skipAssignments=False)
        returns a nbformat.NotebookNode with the student ready notebook.
        skipAssignments is self explanatory.

    to_nb(target_filename,skipAssignments=False)
        writes the notebook to file, it writes the same as
        toLectureNotebook(skipAssignments) to `target_filename`
    """
    #not format specific
    def __init__(self,nb_filename=None, examHeader='', courseDetails=None, header=''): #<< add default parameters 'courseDetails' and 'header'
        """
        Parameters
        ----------
        nb_filename : str
            the filename of the raw notebook to init from.
            if not included, an empty CourseNotebook object
            will be created.
        """
        self.courseDetails = courseDetails
        self.header = header
        self.examHeader = examHeader
        self.assignmentNumbers = []
        self.assignmentCells = []
        if (nb_filename != None):
            self.notebook = self._from_file(nb_filename)
            self.nb_filename = nb_filename

            self._parse_notebook() 
        else:
            self.notebook = None
    
        #some trouble putting in individual classes
    def _from_file(self,nb_filename=None):
        """
        Loads a notebook from file to nbformat.NotebookNode

        Parameters
        ----------
        nb_filename : str
            the filename of the raw notebook to init from
            << This is actually a full path of the file # Added by Suparerk
            << Typcially, master/jp/xxx.ipynb, master/dbc/xxx.dbc # Added by Suparerk

        Returns
        -------
        notebook : nbformat.NotebookNode

        Raises
        ----------
        FileNotFoundException

        """
        raise NotImplementedError("CourseNotebook _from_file implemented in subclasses")
        
       

        #might be tangled up in something
    def _parse_notebook(self):

        """
            This function parses the raw notebook and does the following
            * Identifies all assignment cells and tags them with correct metadata
            * Prepares the assignment cells for student version
            * Appends on that by inserting assignment cells with generic instructions
            * Stores all tagged and prepared assignment cells in self.assignmentCells
            * Inserts / replaces the cells in the self.notebook with the tagged
                and prepared cells
            * Prepare the metadata for the assignment cells and put them in the cell metadata
            * take master NB and turn the #PROBLEM x, #POINT y, #TEST x into md cells
            * ADD PROBLEM number in cell metadata
        """
        raise NotImplementedError("_parse_notebook not implemented")
        
    
        
        #this one is format general
    def getAssignments(self,assignmentNumber=0):
        """
            * Goes through all assignment related cells in this notebook
            * Assembles them into a list of Assignment objects

            Parameters
            ----------
            assignmentNumber : int
                extract Assignments related to this assignmentNumber

            Returns
            -------
            assignment_vector : [Assignment]
                the list of Assignment objects connected to this notebook
                and assignmentNumber
        """

        if (assignmentNumber not in self.assignmentNumbers):
            return None

        assignment_cells = [cell for cell in self.assignmentCells if cell['metadata']['lx_assignment_number'] == str(assignmentNumber)]
        problem_numbers = sorted(list(set([int(cell['metadata']['lx_problem_number']) for cell in assignment_cells])))
        assignment_vector = []
        for problem_num in problem_numbers:
            cells = [cell for cell in assignment_cells if cell['metadata']['lx_problem_number'] == str(problem_num)] #<< Bug from Benny's code << It must be 'assignment_cells', not 'self.assignmentCells'. << This causes failure to the assignment extraction when several problems of the same assignment are put in many master notebooks.
            problem_cells = [cell for cell in cells if cell['metadata']['lx_problem_cell_type'] == 'PROBLEM']
            solution_cells = [cell for cell in cells if cell['metadata']['lx_problem_cell_type'] == 'SOLUTION']
            test_cells = [cell for cell in cells if cell['metadata']['lx_problem_cell_type'] == 'Test']
            TEST_cells = [cell for cell in cells if cell['metadata']['lx_problem_cell_type'] == 'TEST']

            problem_points = problem_cells[0]['metadata']['lx_problem_points']

            assignment_vector.append(Assignment(PROBLEM_Cells = problem_cells,
                                                SOLUTION_Cells = solution_cells,
                                                Test_Cells = test_cells,
                                                TEST_Cells = TEST_cells,
                                                problem_points = problem_points))

        return assignment_vector
    #
        #this one we can generalize
    def _add_course_metadata(self, notebook,metadata_name):
        """
            Add this objects course metadata to a notebook

            Parameters
            ----------
            notebook : nbformat.NotebookNode
                the notebook to add metadata to

            Returns
            -------
            notebook : nbformat.NotebookNode
                the notebook with metadata added
        """
        #either general solution here, or looking forward, keep this class-dependent/specific.
        notebook[metadata_name]['lx_course_number']=self.courseDetails['CourseID']
        notebook[metadata_name]['lx_course_name']=self.courseDetails['CourseName']
        notebook[metadata_name]['lx_course_instance']=self.courseDetails['CourseInstance']


        return notebook

        
    def _add_header(self, notebook,is_dbc=False):
        #TODO: if we change LectureNotebook inherticance to DB/IDSCourseNotebook instead of AssignmentNotebook, we can move this to individual classes.
        """
            Inserts this objects header as the first cell in the notebook

            Parameters
            ----------
            notebook : nbformat.NotebookNode
                The notebook you wish to modify

            Returns
            -------
            notebook : nbformat.NotebookNode
                the notebook with the header cell inserted as first cell
        """
        #raise NotImplementedError("CourseNotebook _add_header is implemented in subclasses.")
        if(is_dbc):
            try:
                if (self.examHeader != ''):
                    newCell_str = '''{
                        "version": "CommandV1",
                        "origId": 2391963185141926,
                        "guid": "f21055aa-ee56-4536-9eb6-d9752d5821b6",
                        "subtype": "command",
                        "commandType": "auto",
                        "position": 0.01,
                        "command": "",
                        "commandVersion": 26,
                        "state": "error",
                        "results": null,
                        "resultDbfsStatus": "INLINED_IN_TREE",
                        "errorSummary": null,
                        "errorTraceType": null,
                        "error": null,
                        "workflows": [],
                        "startTime": 0,
                        "submitTime": 0,
                        "finishTime": 0,
                        "collapsed": false,
                        "bindings": {},
                        "inputWidgets": {},
                        "displayType": "table",
                        "width": "auto",
                        "height": "auto",
                        "xColumns": null,
                        "yColumns": null,
                        "pivotColumns": null,
                        "pivotAggregation": null,
                        "useConsistentColors": false,
                        "customPlotOptions": {},
                        "commentThread": [],
                        "commentsVisible": false,
                        "parentHierarchy": [],
                        "diffInserts": [],
                        "diffDeletes": [],
                        "globalVars": {},
                        "latestUser": "a user",
                        "latestUserId": null,
                        "commandTitle": "",
                        "showCommandTitle": false,
                        "hideCommandCode": false,
                        "hideCommandResult": false,
                        "isLockedInExamMode": false,
                        "iPythonMetadata": null,
                        "metadata": {},
                        "streamStates": {},
                        "datasetPreviewNameToCmdIdMap": {},
                        "tableResultIndex": null,
                        "listResultMetadata": [],
                        "subcommandOptions": null,
                        "nuid": ""
                    }'''

                    newCell = json.loads(newCell_str)

                    # newCell = nbformat.v4.new_markdown_cell(self.examHeader)
                    newCell['command'] = self.examHeader
                    newCell['metadata']['deletable']=False
                    notebook['commands'].insert(0,newCell)

                    # new cell >> anonymous exam id --------------------------------------------------------------------------------------
                    #
                    # newCell = nbformat.v4.new_code_cell('''# Enter your anonymous exam id by replacing XXXX in this cell below
        # # do NOT delete this cell
        # MyAnonymousExamID = "XXX"''')

                    anonymous_cell_content_scala = '''%scala\n// Enter your anonymous exam id by replacing XXXX in this cell below\n// // do NOT delete this cell\n// MyAnonymousExamID = \\"XXXX\\"'''
                    anonymous_cell_content_python = '''%python\n# Enter your anonymous exam id by replacing XXXX in this cell below\n# # do NOT delete this cell\n# MyAnonymousExamID = \\"XXXX\\"'''
                    anonymous_cell_content_r = '''%r\n# Enter your anonymous exam id by replacing XXXX in this cell below\n# do NOT delete this cell\n# MyAnonymousExamID = \\"XXXX\\"'''

                    file_extension = "scala"
                    for filename in os.listdir(self.courseDetails['notebook_folder']):
                        if len(filename.split(".")) == 2:
                            if filename.split(".")[1] not in ["dbc"]:
                                file_extension = filename.split(".")[1]
                                break # get out of for-loop immediately when matched
                    assignmentLanguage = file_extension

                    anonymous_cell_content = anonymous_cell_content_scala
                    if(assignmentLanguage == "scala"):
                        anonymous_cell_content = anonymous_cell_content_scala
                    elif(assignmentLanguage == "python"):
                        anonymous_cell_content = anonymous_cell_content_python
                    elif(assignmentLanguage == "r"):
                        anonymous_cell_content = anonymous_cell_content_r

                    newCell_0_str = '''{
                        "version": "CommandV1",
                        "origId": 3192287633905980,
                        "guid": "9a83a60c-d993-4e52-9ff4-8188ef5d02f7",
                        "subtype": "command",
                        "commandType": "auto",
                        "position": 1.5,
                        "command": "'''
                    newCell_1_str = anonymous_cell_content
                    newCell_2_str = '''",
                        "commandVersion": 19,
                        "state": "error",
                        "results": null,
                        "resultDbfsStatus": "INLINED_IN_TREE",
                        "errorSummary": null,
                        "errorTraceType": null,
                        "error": null,
                        "workflows": [],
                        "startTime": 0,
                        "submitTime": 0,
                        "finishTime": 0,
                        "collapsed": false,
                        "bindings": {},
                        "inputWidgets": {},
                        "displayType": "table",
                        "width": "auto",
                        "height": "auto",
                        "xColumns": null,
                        "yColumns": null,
                        "pivotColumns": null,
                        "pivotAggregation": null,
                        "useConsistentColors": false,
                        "customPlotOptions": {},
                        "commentThread": [],
                        "commentsVisible": false,
                        "parentHierarchy": [],
                        "diffInserts": [],
                        "diffDeletes": [],
                        "globalVars": {},
                        "latestUser": "a user",
                        "latestUserId": null,
                        "commandTitle": "",
                        "showCommandTitle": false,
                        "hideCommandCode": false,
                        "hideCommandResult": false,
                        "isLockedInExamMode": false,
                        "iPythonMetadata": null,
                        "metadata": {},
                        "streamStates": {},
                        "datasetPreviewNameToCmdIdMap": {},
                        "tableResultIndex": null,
                        "listResultMetadata": null,
                        "subcommandOptions": null,
                        "nuid": ""
                    }'''

                    newCell_str = newCell_0_str + newCell_1_str + newCell_2_str
                    newCell = json.loads(newCell_str)

                    newCell['metadata']['deletable']=False
                    notebook['commands'].insert(2,newCell)
            except Exception as e:
                pass
    
            if (self.header != None):
                newCell_str = '''{
                    "version": "CommandV1",
                    "origId": 2391963185141926,
                    "guid": "f21055aa-ee56-4536-9eb6-d9752d5821b6",
                    "subtype": "command",
                    "commandType": "auto",
                    "position": -99999,
                    "command": "",
                    "commandVersion": 26,
                    "state": "error",
                    "results": null,
                    "resultDbfsStatus": "INLINED_IN_TREE",
                    "errorSummary": null,
                    "errorTraceType": null,
                    "error": null,
                    "workflows": [],
                    "startTime": 0,
                    "submitTime": 0,
                    "finishTime": 0,
                    "collapsed": false,
                    "bindings": {},
                    "inputWidgets": {},
                    "displayType": "table",
                    "width": "auto",
                    "height": "auto",
                    "xColumns": null,
                    "yColumns": null,
                    "pivotColumns": null,
                    "pivotAggregation": null,
                    "useConsistentColors": false,
                    "customPlotOptions": {},
                    "commentThread": [],
                    "commentsVisible": false,
                    "parentHierarchy": [],
                    "diffInserts": [],
                    "diffDeletes": [],
                    "globalVars": {},
                    "latestUser": "a user",
                    "latestUserId": null,
                    "commandTitle": "",
                    "showCommandTitle": false,
                    "hideCommandCode": false,
                    "hideCommandResult": false,
                    "isLockedInExamMode": false,
                    "iPythonMetadata": null,
                    "metadata": {},
                    "streamStates": {},
                    "datasetPreviewNameToCmdIdMap": {},
                    "tableResultIndex": null,
                    "listResultMetadata": [],
                    "subcommandOptions": null,
                    "nuid": ""
                }'''

                newCell = json.loads(newCell_str)

                #newCell = nbformat.v4.new_markdown_cell(self.header)
                newCell['command'] = "%md\n"+self.header
                newCell['metadata']['deletable']=False
                notebook['commands'].insert(0,newCell)

            return notebook

        else: # ipynb
            try:
                if (self.examHeader != ''):
                    newCell = nbformat.v4.new_markdown_cell(self.examHeader)
                    newCell['metadata']['deletable']=False
                    notebook['cells'].insert(0,newCell)

                    newCell = nbformat.v4.new_code_cell('''# Enter your anonymous exam id by replacing XXXX in this cell below
        # do NOT delete this cell
        MyAnonymousExamID = "XXXX"''')
                    newCell['metadata']['deletable']=False
                    notebook['cells'].insert(2,newCell)
            except Exception as e:
                pass
            if (self.header != None):
                newCell = nbformat.v4.new_markdown_cell(self.header)
                newCell['metadata']['deletable']=False
                notebook['cells'].insert(0,newCell)
            return notebook


        #this one we can generalize
    def toLectureNotebook(self,skipAssignments=False,is_dbc=False):
        """
            Prepares a version of this notebook suitable for lectures

            Parameters
            ----------
            skipAssignments : bool
                if the assignments should be in the output or not

            Returns
            -------
            notebook : nbformat.NotebookNode
                the prepared student version of a notebook, with or without
                the assignements
        """
        lectureNotebook = self.notebook.copy()
        #removed if statement. This might cause jp to temporarily crash
        # Begin by generating the metadata
        lectureNotebook = self._add_course_metadata(lectureNotebook,self.cellNameForMetadata) # <<<<<<<<

        # Add the cell with header to this notebook
        lectureNotebook = self._add_header(lectureNotebook) # <<<<<<<<


        # Remove the TEST and SOLUTION cells from the lecture notebook
        # You need to have parsed the notebook to make sure that the assignment data is
        # now in the metadata of the notebook.

        studentCells=[]
        for cell in self.notebook[self.cellName]:
            appendCell=True
            if 'lx_problem_cell_type' in cell['metadata']:
                probCellType = cell['metadata']['lx_problem_cell_type']
                if ( ("SOLUTION" in probCellType) or ("TEST" in probCellType) or skipAssignments):
                    appendCell=False
            if appendCell:
                studentCells.append(cell)

        lectureNotebook[self.cellName]=studentCells
        
        return lectureNotebook
    
        
    
    def to_nb(self,target_filename,skipAssignments=False):
        '''
            Prepares a lecture worthy notebook and writes it to file

            Parameters
            ----------
            target_filename : str
                The target filename
            skipAssignments : bool
                if assignments should be in the lecture notebook or not.
        '''
        raise NotImplementedError("CourseNotebook to_nb is implemented in individual classes.")
 
class AssignmentNotebook(CourseNotebook):
    """
    Represents an assignment notebook

    Parameters
    ----------
    assignmentNumber : int
        The assignment number of this notebook
    courseNotebooks : [CourseNotebook]
        All the course notebooks that contains the assignments
    assignments : [Assignment]
        all the assignments in this assignment notebook

    Methods
    -------
    to_nb(target_filename,notebook_type='problem_solution_TEST')
        Creates a notebook and writes it to file.
    to_notebook(notebook_type='problem_solution_TEST')
        load a notebook file and turn it into a JSON-format
    __add__(assignmentNotebook)
        assignmentNotebook1 + assignmentNotebook2 yields a new AssignmentNotebook that has the entire
        assignmentNotebook1 + the TESTS from assignmentNotebook
    numProblems()
        the number of Assignments in this AssignmentNotebook

    numTests()
        How many pure TEST Assignments we have

    extractResult()
        Extracts the result of a graded notebook
    """
    def __init__(self,courseNotebooks = None,assignmentNumber = 1):
        """
        Parameters
        ----------
        courseNotebooks : [CourseNotebook]
            the list of courseNotebooks to build this AssignmentNotebook on
        assignmentNumber : int
            the assignment number related to this AssignmentNotebook
        """
        self.assignmentNumber = assignmentNumber
        self.courseNotebooks = courseNotebooks
        if (courseNotebooks != None):
            self.assignments = [courseNotebook.getAssignments(self.assignmentNumber) for courseNotebook in courseNotebooks]
            self.assignments = list(filter(None.__ne__, self.assignments)) # Remove the empty entries
            self.assignments = sum(self.assignments,[]) # Make a flattened list out of list of lists

    
    def _add_assignment_metadata(self,notebook):
        #raise NotImplementedError("AssignmentNotebook _add_assignment_metadata is implemented in individual classes.")

        notebook[self.cellNameForMetadata]['lx_assignment_number']=self.assignmentNumber

        return notebook
        #create a sub-function ,write to file or something when using subclass-speicifc formating
    @staticmethod
    def injectTestCells(notebook,cells):
        TEST_cells = []   
        for i in notebook[cells]:
            try:
                if i['metadata']['lx_problem_cell_type'] == 'TEST':
                    TEST_cells += [i]
                else:
                    pass
            except Exception as e:
                pass
        
        new_commands = []
        counter=0
        last = notebook[cells][0]
        for i in notebook[cells]:
            if 'lx_problem_cell_type' not in i['metadata']:
                new_commands += [i]
            elif i['metadata']['lx_problem_cell_type'] == 'PROBLEM':
                new_commands += [i]
            elif i['metadata']['lx_problem_cell_type'] == 'Test' or i['metadata']['lx_problem_cell_type'] == 'SOLUTION':
                new_commands += [i]              
                try:
                    if (i['metadata']['lx_problem_cell_type'] == 'Test' and last['metadata']['lx_problem_cell_type'] == 'Test') or (i['metadata']['lx_problem_cell_type'] == 'SOLUTION' and new_commands[-2]['metadata']['lx_problem_cell_type'] == 'SOLUTION'):
                        #We have to look and new_commands[-2] instead of "last" because "last" will always be a solution cell in the case of submitting an Assignment_solution notebook
                        #we want support for this so that it is possible to submit it as the "model" student.
                        new_commands += [TEST_cells[counter]]
                        counter += 1
                except Exception as e:
                     pass
            last = i
        #disgusting temporary loop:
        #do this in the beginning of the function
        notebook[cells] = []
        for cell in new_commands:
            notebook[cells] += [cell]
        return notebook

    def to_nb(self, target_filename,notebook_type='problem_solution_TEST'):
        """
        Creates a notebook and writes it to file.

        Parameters
        ----------
        target_filename : str << .ipynb, .scala, .py, .r, ... << not .dbc !!!
        notebook_type : str
            a string of type "x_y_z_..." where we can use "problem", "solution", "TEST"
            to determine which cells should be present in the output.
            "problem" includes the problem and self test.
            "solution" only includes the solution.
            "TEST" includes the final test of the problem
        """
        source_file_path = "/".join(target_filename.split("/")[0:-1]) # lectures
        source_file_name = target_filename.split("/")[-1].split(".")[0] # 00, 01, etc
        source_file_extension = target_filename.split(".")[-1] # py, scala, etc

        if(source_file_extension != "ipynb"): # source file as .scala, .py, etc that will be zipped into .dbc
            assignmentNotebook = self.to_notebook(notebook_type=notebook_type,notebook_language=source_file_extension) # get a notebook (dict) with cells that belong to a specific type

            # write as source file (.scala, .py, etc)
            with open(target_filename, mode='w') as f:
                # nbformat.write(assignmentNotebook,f)
                json.dump(assignmentNotebook, f)

            # then we have to zip it into dbc
            # path_to_dbc_target_file = source_file_path+"/"+source_file_name+".dbc" (destination)
            # path_to_source_file_to_be_zipped = target_filename = source_file_path+"/"+source_file_name+"."+file_extension (source)
            # source_file_name_with_extension = source_file_name+"."+source_file_extension
            with ZipFile(source_file_path+"/"+source_file_name+".dbc", 'w') as zipObj:
                zipObj.write(target_filename, source_file_name+"."+source_file_extension) #<< Finally got it as .dbc !

            # remove source file, so only .dbc is left
            os.remove(target_filename)

        else: #.ipynb
            assignmentNotebook = self.to_notebook(notebook_type=notebook_type)

            with open(target_filename, mode='w') as f:
                nbformat.write(assignmentNotebook,f)
        pass   

    def to_notebook(self,notebook_type='problem_solution_TEST',notebook_language=""):
        '''
        Creates a notebook

        Parameters
        ----------
        notebook_type : str
            a string of type "x_y_z_..." where we can use "problem", "solution", "TEST"
            to determine which cells should be present in the output.
            "problem" includes the problem and self test.
            "solution" only includes the solution.
            "TEST" includes the final test of the problem
        
        is_dbc : Boolean <<<< This parameter is added by Suparerk.
            True if the notebook to make is .dbc
            False if the notebook to make is .ipynb

        Returns
        -------
        notebook : nbformat.NotebookNode
            the ready made assignment Notebook.

        '''
        raise NotImplementedError("AssignmentNotebook to_notebook is implemented in subclasses.")
        pass
  
    def _load_notebook(self,nb_filename): #<< full path
        # called from AutoGrader.py > prepareNotebookForGrading > IDSAss > __init__
        # nb_filename = student_nb_filename -- the filename of the student notebook << eg. "StudentSubmission/<Student_ID>_<attempt>.ipynb"
        # nb_filename = master_soln_nb_filename -- the filename of the notebook that contains the tests << eg. "Master/Assignment_XXX_problem_TEST.ipynb" << loaded from config.json
        """
        Loads a notebook from file
        """
        print("Loading notebook: %s" % nb_filename)
        # with open(nb_filename,mode='r') as f:
        #     notebook = nbformat.read(f,as_version=4)
        # return notebook

        file_path = "/".join(nb_filename.split("/")[0:-1]) # StudentSubmission
        nb_name = nb_filename.split("/")[-1].split(".")[0]
        file_extension = nb_filename.split(".")[-1] # dbc, ipynb, scala, python

        #load scala or python
        if(file_extension in ["scala","python"]):
            # read it
            with open(nb_filename, 'r') as f:
                raw_file = f.read()

            nb = json.loads(raw_file)

            # remove source file and manifest.mf we got from the zip extraction
            os.remove(nb_filename) 
            try:
                #print("manifest.mf used to be removed here")
                os.remove(os.path.join(file_path, "manifest.mf"))
                
            except:
                #print("manifest.mf not found")
                pass

        #load dbc
        elif(file_extension in ["dbc"]):
            # First, unzip it !
            print("load dbc, and unzip file")
            with ZipFile(nb_filename, 'r') as zipObj: # nb_filename is a full path to .dbc file ! not just a file name !
                # Unzip .dbc into the same directory, yielding a file in .scala, .py, etc., in which the content is in a json format !
                zipObj.extractall(file_path) # Extract dbc to StudentSubmission
                namelist_in_zip = [file_name for file_name in zipObj.namelist() if file_name.split(".")[-1] not in ["mf","dbc"]]

                if len(namelist_in_zip) == 1 :
                    source_file_name = namelist_in_zip[0]
                elif len(namelist_in_zip) > 1 :
                    print("Please remove all source files first ! Return None.")
                    return json.loads("{}") # return empty dict << may raise error at a later point
                else:
                    print("No file matched from the unzipped files. Return None.")
                    return json.loads("{}") # return empty dict << may raise error at a later point

                

                # read it
                with open(os.path.join(file_path, source_file_name), 'r') as f:
                    raw_file = f.read()

                nb = json.loads(raw_file)

                # remove source file and manifest.mf we got from the zip extraction
                os.remove(os.path.join(file_path, source_file_name)) 
                try:
                    os.remove(os.path.join(file_path, "manifest.mf"))
                except:
                    print("error in deleting manifest in AssignmentNotebook 2")
        
        #load Jupyter
        elif(file_extension == "ipynb"):
            with open(nb_filename,mode='r') as f:
                nb = nbformat.read(f,as_version=4)


        else:
            print("file extension: ", file_extension)
            print("\nNotebook type not supported. Return None.\nAssignmentNotebook.py, class AssignmentNotebook() -> method _load_notebook()\n")
            return json.loads("{}") # may raise error at a later point

        return nb
        

    def _extractCourseDetails(self,notebook): # notebook loaded from _load_notebook above. this is just a json.
        # called from AutoGrader.py > prepareNotebookForGrading > IDSAss > __init__
        
        details={}
        assignmentNumber = -1

        #if "notebookMetadata" in notebook: # dbc
        metadatacellname = self.getMetaDataCellName(notebook)
        try:
            details['CourseID']=notebook[metadatacellname]['lx_course_number']
        except:
            print("Course ID is not in metadata of input notebook")
        try:
            details['CourseName']=notebook[metadatacellname]['lx_course_name']
        except:
            print("Course Name is not in metadata of input notebook")
        try:
            details['CourseInstance']=notebook[metadatacellname]['lx_course_instance']
        except:
            print("Course Instance is not in metadata of input notebook")
        try:
            assignmentNumber=notebook[metadatacellname]['lx_assignment_number']
        except:
            print("Course Assignment Number is not in metadata of input notebook")

        
        return details,assignmentNumber
        

        
    def _extractHeader(self,notebook):
        if "notebookMetadata" in notebook: # dbc
            return notebook['commands'][0]['command']
        elif "nbformat" in notebook: #ipynb
            return notebook['cells'][0]['source']
        else:
            print("Notebook format not supported.")
            return json.loads("{}") #return empty cell

    def _extractProblems(self,notebook):
        if "notebookMetadata" in notebook: # dbc
            cells_ = "commands"
            source_ = "command"
        elif "nbformat" in notebook: # ipynb
            cells_ = "cells"
            source_ = "source"
        else:
            print("Notebook format not supported.")
            return [] #return empty list
        
        # ---

        problems = {}

        for cell in notebook[cells_]:
            metadata = cell['metadata']
            source = cell[source_]

            if ('lx_problem_number' in metadata):
                problemNumber = metadata['lx_problem_number']

                if (metadata.get('lx_test_only',"False") == "True"):
                    problems['TEST_'+str(problemNumber)] = {metadata['lx_problem_cell_type']:[cell],
                                                            'lx_problem_points':metadata['lx_problem_points']}
                elif (problemNumber not in problems):
                    problems[problemNumber] = {metadata['lx_problem_cell_type']:[cell],
                                            'lx_problem_points':metadata['lx_problem_points']}
                else:
                    if (metadata['lx_problem_cell_type'] not in problems[problemNumber]):
                        problems[problemNumber][metadata['lx_problem_cell_type']] = [cell]
                    else:
                        problems[problemNumber][metadata['lx_problem_cell_type']]+=[cell]

        assignments = []

        for problem in problems:
            if ('TEST' not in problem):
                PROBLEM_Cells = problems[problem].get('PROBLEM',[])
                Test_Cells = problems[problem].get('Test',[])
                SOLUTION_Cells = problems[problem].get('SOLUTION',[])
                TEST_Cells = problems[problem].get('TEST',[])
                problem_points = problems[problem]['lx_problem_points']
                assignments.append(Assignment(PROBLEM_Cells=PROBLEM_Cells, # class Assignment is compatible with both dbc and ipynb. Nothing to be changed there.
                                            SOLUTION_Cells=SOLUTION_Cells,
                                            Test_Cells=Test_Cells,
                                            TEST_Cells=TEST_Cells,
                                            problem_points = problem_points))
        for problem in problems:
            if ('TEST' in problem):
                PROBLEM_Cells = problems[problem].get('PROBLEM',[])
                Test_Cells = problems[problem].get('Test',[])
                SOLUTION_Cells = problems[problem].get('SOLUTION',[])
                TEST_Cells = problems[problem].get('TEST',[])
                problem_points = problems[problem]['lx_problem_points']
                assignments.append(Assignment(PROBLEM_Cells=PROBLEM_Cells, # class Assignment is compatible with both dbc and ipynb. Nothing to be changed there.
                                            SOLUTION_Cells=SOLUTION_Cells,
                                            Test_Cells=Test_Cells,
                                            TEST_Cells=TEST_Cells,
                                            problem_points = problem_points))
        
        return assignments
        
    def __add__(self,assignmentNotebook):
        """
        Takes this notebook and appends the tests of the other notebook

        Parameters
        ----------
        assignmentNotebook : AssignmentNotebook
            the notebook that contains the tests

        Returns
        -------
        notebook : AssignmentNotebook
            a notebook with the tests of assignmentNotebook added at the end
        """
        raise NotImplementedError("AssignmentNotebook __add__ is implemented in subclasses.")
    
    def __repr__(self):
        info = "CourseID: %s, CourseName: %s, CourseInstance: %s \n" % (self.courseDetails['CourseID'],
                                                                        self.courseDetails['CourseName'],
                                                                        self.courseDetails['CourseInstance'])


        info2 = "Number of assignments: %d, Number of pure tests: %d \n" % (self.numProblems(),self.numTests())
        assignments = '\n'.join([str(ass) for ass in self.assignments])
        return info+info2+assignments
   

    #generalize this
    def getMetaDataCellName(self,notebook):
        if "notebookMetadata" in notebook:
            return "notebookMetadata"
        if "metadata" in notebook:
            return "metadata"
        else:
            print("not supported")
            return None 
    def numProblems(self):
        """
        Returns
        --------
        num : int
            the number of problems in this assignment
        """
        return len([ass for ass in self.assignments if len(ass.PROBLEM_Cells) > 0])
        
    def numTests(self):
        """
        Returns
        --------
        num : int
            the number of pure TESTS in this assignment
        """
        return len([ass for ass in self.assignments if len(ass.PROBLEM_Cells) == 0 and len(ass.TEST_Cells) > 0])

        #separating for now. see if generalizable
    def extractResult(self):
        """
        Extracts the results of a graded assignment notebook

        Returns
        -------
        finalGradesDict : dict
            a dictionary with the following keys:
            lx_problem_total_scored_points : the total score for this assignment
            lx_problem_total_possible_points : how many possible points in this assignment
        stdOutString : str
            contains the result as a string, that can be reported back to the
            student.
        """
        raise NotImplementedError("AssignmentNotebook extractResult is implemented in subclasses.")

    def nb_as_json(self,notebook_language):
        """
        Returns the notebook as a json object.
        """
        raise NotImplementedError("AssignmentNotebook nb_as_json is implemented in subclasses.")
    
    @staticmethod #want to call this without having to create an instance
    def createAssignmentNotebook(extension = None,nb_filename=None, notebook=None,courseNotebooks = None,assignmentNumber = 1):
        """
        Creates an instance of a subclass of AssignmentNotebook from a notebook file.
        """
        #pass i in args inst of this mess.
        #nb_format = nb_filename.split('.')[-1]
        if extension in ['ipynb','py']:
            from .IDSAssignmentNotebook import IDSAssignmentNotebook
            return IDSAssignmentNotebook(nb_filename=nb_filename,courseNotebooks=courseNotebooks,assignmentNumber=assignmentNumber,notebook=notebook)
            
        elif extension in ['dbc','scala','python']:
            from .DBAssignmentNotebook import DBAssignmentNotebook
            return DBAssignmentNotebook(nb_filename=nb_filename,courseNotebooks=courseNotebooks,assignmentNumber=assignmentNumber,notebook=notebook)
            
        print("Notebook format not recognized")
        pass


class Assignment():
    """
    Represents a problem (or Assignment) in an AssignmentNotebook

    Parameters
    ----------
    PROBLEM_Cells : [dict]
        This is the list of all notebook cells that has the tag PROBLEM.
        This is the problem description and solution skeleton.
    SOLUTION_Cells : [dict]
        This is the list of all notebook cells that has the tag SOLUTION.
        These are the proposed solution cells.
    Test_Cells : [dict]
        This is the list of all notebook cells that has the tag Test. These
        are the self tests (local tests)
    TEST_Cells : [dict]
        This is the list of all notebook cells that has the tag TEST.
        These are the final tests for the assignment, there should actually only
        be one.

    Methods
    -------
    amITEST()
        returns if this is a TEST only assignment. I.e. there are no,
        problem,solution,Test cells but only TEST cells.
    """
    def __init__(self,PROBLEM_Cells,SOLUTION_Cells,Test_Cells,TEST_Cells,problem_points):
        self.PROBLEM_Cells=PROBLEM_Cells
        self.SOLUTION_Cells=SOLUTION_Cells
        self.Test_Cells=Test_Cells
        self.TEST_Cells=TEST_Cells
        self.problem_points = problem_points

    def getProblemNumber(self):
        all_cells = self.PROBLEM_Cells+self.SOLUTION_Cells+self.Test_Cells+self.TEST_Cells
        any_cell = all_cells[0]
        return any_cell['metadata']['lx_problem_number']

    def __repr__(self):
        return "This is an assignment with %d problem cells, %d Solution cells, %d Test cells and %d TEST cells and problem number %s"\
                 % (len(self.PROBLEM_Cells),
                    len(self.SOLUTION_Cells),
                    len(self.Test_Cells),
                    len(self.TEST_Cells),
                    self.getProblemNumber())

    def __str__(self):
        return self.__repr__()

    def amITEST(self):
        if (len(self.TEST_Cells) == 1):
            return True
        else:
            return False

class CourseDetails():
    """
        Representing the details of the course. Works like a dictionary but
        with some extra bells and whistles at init time.

        Keys
        ----
        'CourseID'       : The course number used by UU
        'CourseName'     : The human readable course name
        'CourseInstance' : The year it is given
    """
    def __init__(self,detailsDict):
        assert ('CourseID' in detailsDict), "The dict must contains the information about ['CourseID','CourseName','CourseInstance']"
        assert ('CourseName' in detailsDict), "The dict must contains the information about ['CourseID','CourseName','CourseInstance']"
        assert ('CourseInstance' in detailsDict), "The dict must contains the information about ['CourseID','CourseName','CourseInstance']"

        self.detailsDict = detailsDict
        pass

    def __getitem__(self,x):
        return self.detailsDict[x]

    def __eq__(self,x):
        return ((self.detailsDict['CourseID'] == x['CourseID']) and
                (self.detailsDict['CourseName'] == x['CourseName']) and
                (self.detailsDict['CourseInstance'] == x['CourseInstance']))


    