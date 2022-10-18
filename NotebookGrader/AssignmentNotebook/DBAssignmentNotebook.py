from .AssignmentNotebook import *

#some functions are moved from AssignmentNoteook to here since they included both jupyter
# and db specific code. They will be overrided in this code, and we can call 
# the superclass definition for any shared code. 

class DBCourseNotebook(CourseNotebook):
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

    self.meta = "notebookMetadata"
    
    Methods
    -------
    getAssignments(assignmentNumber=0)
        returns the problems found in this courseNotebook related to
        assignmentNumber

    toLectureNotebook(skipAssignments=False)
        returns a nbformat.NotebookNode with the student ready notebook.
        skipAssignments is self explanatory.
    
    ###only one used###
    to_nb(target_filename,skipAssignments=False)
        writes the notebook to file, it writes the same as
        toLectureNotebook(skipAssignments) to `target_filename`
    """
    def __init__(self,nb_filename=None, examHeader='', courseDetails=None, header=''):
        self.cellNameForMetadata = "notebookMetadata"
        self.cellName = "commands"
        if (nb_filename != None):
            self.notebook = self._from_file(nb_filename)
            self.nb_filename = nb_filename
        super().__init__(nb_filename, examHeader, courseDetails, header)


    

    def _from_file(self,nb_filename=None):
        """
        Loads a notebook from file to nbformat.NotebookNode

        Parameters
        ----------
        nb_filename : str
            the filename of the raw notebook to init from
            << This is actually a full path of the file
            << Typcially, master/jp/xxx.ipynb, master/dbc/xxx.dbc 

        Returns
        -------
        notebook : nbformat.NotebookNode

        Raises
        ----------
        FileNotFoundException

        """

        #load dbc

        #lots of comments here in the original code. See the other branch when cleaning up
        print("load dbc, and unzip file")

        file_path = self.courseDetails['notebook_folder'] # master/dbc
        
        with ZipFile(nb_filename, 'r') as zipObj:
        # with ZipFile(nb_filename, 'r') as zipObj: # nb_filename is a full path to .dbc file ! not just a file name !
            # Unzip .dbc into the same directory, yielding a file in .scala, .py, etc., in which the content is in a json format !
            zipObj.extractall(file_path) # master/dbc
            namelist_in_zip = [file_name for file_name in zipObj.namelist() if file_name.split(".")[-1] not in ["mf"]]

            if len(namelist_in_zip) == 1 :
                source_file_name = namelist_in_zip[0]
            elif len(namelist_in_zip) > 1 :
                print("Please remove all source files first ! Return None.")
                return json.loads("{}") # return empty dict << may raise error at a later point
            else:
                print("No file matched from the unzipped files. Return None.")
                return json.loads("{}") # return empty dict << may raise error at a later point

            # source_file_extension = source_file_name.split(".")[-1]

            with open(os.path.join(file_path, source_file_name), 'r') as f:
                    raw_file = f.read()

            nb = json.loads(raw_file)

            # remove source file and manifest.mf we got from the zip extraction
            os.remove(os.path.join(file_path, source_file_name)) 
            #os.remove(os.path.join(file_path, "manifest.mf"))
    

        return nb


    def _parse_notebook(self):
        """
            This function parses the raw notebook and does the following
            * Identifies all assignment cells and tags them with correct metadata
            * Prepares the assignment cells for student version
            * Appends on that by inserting assignment cells with generic instructions
            * Stores all tagged and prepared assignment cells in self.assignmentCells
            * Inserts / replaces the cells in the self.notebook with the tagged
                and prepared cells
        """
        # Prepare the metadata for the assignment cells and put them in the cell metadata
        # take master NB and turn the #PROBLEM x, #POINT y, #TEST x into md cells
        #    ADD PROBLEM number in cell metadata
        #    TODO? make dictionary of points scored, etc.

        # -----------------------------------------------------------------------------------------
        # parse dbc
        #
        print("Parsing dbc notebook")

        cellIndex=-1
        AssnProbSolDict={}
        indicesToInsertCells=[]

        # commands with unsorted positions of cells
        commands = self.notebook['commands'] # list of cells. each cell is dict. (list of dict)

        # from this point, commands are sorted by position
        # sort cells in commands by position
        commands = sorted(commands, key=lambda cell: cell['position'], reverse=False)

        for cell in commands: # loop through each cell (already sorted by postion) in commands
            cellIndex=cellIndex+1
            
            source = cell['command']
            source_lines = source.split('\n')

            first_line = source_lines[0] # first line
            matchObj_magic = re.match(r'%(\w+)', first_line, re.U) # %scala, %r, %python, etc.
            if matchObj_magic:
                magic_line = first_line+"\n"
                
                x=1
                while(source_lines[x]==''): # skip blank lines
                    x += 1
                header_line = source_lines[x] # maybe or maybe not a header <<<<<<<<<<<<<<<<<

                content = ""
                if(x+1 < len(source_lines)):
                    content = '\n'.join(source_lines[x+1:]) # after header_line until the end # gives '' if no extra lines are there

            else:
                magic_line = ""
                header_line = first_line # = source_lines[0] # maybe or maybe not a header

                content = ""
                if(len(source_lines)>=2):
                    content = '\n'.join(source_lines[1:]) # second line until the end # gives '' if no extra lines are there
            
            # Example matches (starting exactly with # or //)
            # # Assignment 1, Problem 2, Points 3
            # // Assignment 1, Problem 2, Points 3
            matchObj = re.match(r'^(?:#|//)\s*(\w+)\s+(\w+),\s*(\w+)\s+(\d+),\s*(\w+)\s*(\d+)', header_line, re.U)

            if matchObj:
                #print cellIndex, l0

                # group 1 - ASSIGNMENT, or EXAM
                assignmentType = str(matchObj.group(1)) # ASSIGNMENT
                if assignmentType=='ASSIGNMENT':
                    assignmentType2Print='Assignment'
                else:
                    assignmentType2Print='Exam'

                # group 2 - Assignment Number
                assignmentNum = str(matchObj.group(2))

                try:
                    if (int(assignmentNum) not in self.assignmentNumbers):
                        self.assignmentNumbers.append(int(assignmentNum))
                except ValueError as e:
                    if (assignmentNum not in self.assignmentNumbers):
                        self.assignmentNumbers.append(assignmentNum)

                # group 3 - PROBLEM, SOLUTION, Test or TEST
                cell_type = matchObj.group(3) 

                # group 4 - Problem Number
                probNum=str(int(matchObj.group(4))) 

                # group 5 is just a string 'Points', so we skip this.

                # group 6 - Problem Points
                probPoints=str(int(matchObj.group(6))) 

                # dbc json uses the same name for cell metadata, and also exactly at the same level, so no need to change anything here.
                cell['metadata']['lx_assignment_type']=assignmentType
                cell['metadata']['lx_assignment_type2print']=assignmentType2Print
                cell['metadata']['lx_assignment_number']=assignmentNum
                cell['metadata']['lx_problem_cell_type']=cell_type
                cell['metadata']['lx_problem_number']=probNum
                cell['metadata']['lx_problem_points']=probPoints
                cell['metadata']['deletable']=False # this is to make sure cells of this type are non-deletable

                if (cell_type == 'PROBLEM' or cell_type == 'SOLUTION' or cell_type == 'Test'):
                    cell['command'] = magic_line+content # remove header line comment. keep the magic_line if exist. <<<<
                    if assignmentNum+'_'+probNum+'_'+cell_type not in AssnProbSolDict:
                        if(cell_type != 'Test'):
                            #md='''---\\n## Assignment {}, {} {}\\nMaximum Points = {}'''.format(assignmentNum,LX_Prob_CellType,probNum,probPoints)
                            md='''---\\n## {} {}, {} {}\\nMaximum Points = {}'''.format(assignmentType2Print,assignmentNum,cell_type,probNum,probPoints)
                        else:
                            md='''---\\n#### Local {} for {} {}, PROBLEM {}\\nEvaluate cell below to make sure your answer is valid. You **should not** modify anything in the cell below when evaluating it to do a local test of your solution.\\nYou may need to include and evaluate code snippets from lecture notebooks in cells above to make the local test work correctly sometimes (see error messages for clues). This is meant to help you become efficient at recalling materials covered in lectures that relate to this problem. Such local tests will generally not be available in the exam.'''.format(cell_type,assignmentType2Print,assignmentNum,probNum)

                        # newCell = nbformat.v4.new_markdown_cell(md) #<<<<<<<<<<<<<
                        # newCell['metadata'] = cell['metadata']
                        
                        # newCell with position = -1. To be renumbered later in the code.
                        newCell_0_str = '''{
                            "version": "CommandV1",
                            "origId": 2391963185141926,
                            "guid": "f21055aa-ee56-4536-9eb6-d9752d5821b6",
                            "subtype": "command",
                            "commandType": "auto",
                            "position": -1,
                            "command": "%md\\n'''
                        newCell_1_str = md
                        newCell_2_str = '''",
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

                        newCell_str = newCell_0_str + newCell_1_str + newCell_2_str

                        newCell = json.loads(newCell_str) # newCell as dict
                        newCell['metadata'] = cell['metadata']

                        indicesToInsertCells.append([cellIndex,newCell])
                        self.assignmentCells.append(newCell)
                        cellIndex=cellIndex+1
                        AssnProbSolDict[assignmentNum+'_'+probNum+'_'+cell_type]=1
                        
                self.assignmentCells.append(cell)

        # renumber self.assignmentCells << list of cell and newCell as dict (only those that match header and only for cell_type = PROBLEM, SOL, Test)
        new_index = 0
        for cell in self.assignmentCells:
            cell['position'] = new_index
            new_index += 1

        # now insert the md cells at the right places
        for iC in indicesToInsertCells:
            commands.insert(iC[0],iC[1]) # We get self.notebook['commands'] as list of dict!

        # renumber commands
        new_index = 0
        for cell in commands:
            cell['position'] = new_index
            new_index += 1

        # put commands back to self.notebook
        self.notebook['commands'] = commands
      

    def _add_header(self, notebook):
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
            # save as source file
        with open(target_filename,mode='w') as f:
            json.dump(self.toLectureNotebook(skipAssignments,is_dbc=True), f) # dump dict into a json file

        # zip
        source_file_path = "/".join(target_filename.split("/")[0:-1]) # lectures
        source_file_name = target_filename.split("/")[-1].split(".")[0] # 00, 01, etc
        source_file_extension = target_filename.split(".")[-1] # py, scala, etc

        with ZipFile(source_file_path+"/"+source_file_name+".dbc", 'w') as zipObj:
            zipObj.write(target_filename, source_file_name+"."+source_file_extension)

        # remove source file, so only .dbc is left
        os.remove(target_filename)
        
        


class DBAssignmentNotebook(AssignmentNotebook):
    """
    Represents an assignmentNotebook for Introduction to Data Science (IDS)
    Extends on AssignmentNotebook but has some extra bells and whistles.

    * The difference being that you can initialize empy
    * initialize from a file
    * initialize from a notebook
    """


        #this init is identical as in corresponding db-class. maybe create a second init or something
    def __init__(self,courseNotebooks = None,assignmentNumber = 1,nb_filename=None, notebook=None):
        self.notebook = None
        self.cellNameForMetadata = "notebookMetadata"
        self.cellName = "commands"

        if (nb_filename != None): # called from AutoGrader.py > prepareNotebookForGrading
            self.notebook = self._load_notebook(nb_filename) #<< Done
            self.courseDetails, self.assignmentNumber = self._extractCourseDetails(self.notebook) #<< Done
            assert self.courseDetails == DBCourseDetails() # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
            self.header = self._extractHeader(self.notebook) #<< Done
            self.assignments = self._extractProblems(self.notebook) #<< Done
            print("nb_filename",nb_filename)
            self.assignmentFileName = nb_filename 
        elif courseNotebooks != None:
            self.courseDetails = DBCourseDetails()
            self.assignmentNumber = assignmentNumber
            CourseID = self.courseDetails['CourseID']
            self.header = '''%md\n# Assignment {} for Course {}\nMake sure you pass the `# ... Test` cells and\n submit your solution notebook in the corresponding assignment on the course website. You can submit multiple times before the deadline and your highest score will be used.'''.format(self.assignmentNumber,CourseID,CourseID,self.assignmentNumber)

            super().__init__(courseNotebooks, assignmentNumber)
        elif (notebook!=None): # called from AutoGrader.py > safeRunNotebook
            self.notebook = notebook
            self.courseDetails, self.assignmentNumber = self._extractCourseDetails(self.notebook)
            self.header = self._extractHeader(self.notebook)
            self.assignments = self._extractProblems(self.notebook)
        else:
            self.courseDetails = DBCourseDetails()
            self.header = None
            self.assignments = None
            self.assignmentNumber = None
            self.courseNotebooks = None



    
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

        #Lets add the tests for this one to the end
        assert(self.courseDetails == assignmentNotebook.courseDetails), "Assignment notebook courseDetails doesn't match. Check if course details in config.json in AssignmentNotebook are all correct and matched with student submision notebooks. Or, students might submit wrong notebooks." #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

        # check if notebook is dbc or ipynb
        # >> In case 'if' below doesn't work, use these following two lines instead. Also remove assignmentsWithTest inside if and elif !
        assignmentsWithTest = [assignment for assignment in assignmentNotebook.assignments if len(assignment.TEST_Cells) > 0]  #<< swtich0
        if "command" in assignmentsWithTest[0].TEST_Cells[0]:  #<< swtich0
            notebook_default_langauge = assignmentNotebook.notebook['language']
            print("notebook default lang = "+notebook_default_langauge)

            if notebook_default_langauge not in ["python","scala"]:
                print("Notebook language not supported. Currently support only python and scala.")
                returnNB = AssignmentNotebook()
                returnNB.assignments = []
                return returnNB #return empty assignment notebook
            # --------

            tests = []

            # get only TEST cells
            # assignmentsWithTest = [assignment for assignment in assignmentNotebook.assignments if len(assignment.TEST_Cells) > 0] # << swtich1

            # template for a new code cell
            # do not forget to set the position of the cell
            newCell_str = '''{
                "version": "CommandV1",
                "origId": 688636870109868,
                "guid": "d5aa5402-7de1-4eff-bd92-be1476fe8577",
                "subtype": "command",
                "commandType": "auto",
                "position": -1,
                "command": "",
                "commandVersion": 3,
                "state": "finished",
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
                "metadata": {
                    "TEST_Cell_Initialize_or_Total": false
                },
                "streamStates": {},
                "datasetPreviewNameToCmdIdMap": {},
                "tableResultIndex": null,
                "listResultMetadata": null,
                "subcommandOptions": null,
                "nuid": "3d286397-92b5-4837-92a0-e513626e6569"
                }'''
            
            # this counter can be used for both python and scala !
            counter_str = '''\ncumPoints = cumPoints + local_points\ncumMaxPoints = cumMaxPoints + maxPoints\n'''

            # score string for each problem
            prob_score_python_str = '''\n\nprint(\"The number of points you have scored for this problem is \" + str(local_points) + \" out of \" + str(maxPoints) +\"\\n\")'''
            prob_score_scala_str = '''\n\nprintln(\"The number of points you have scored for this problem is \" + local_points + \" out of \" + maxPoints +\"\\n\")'''
            cumThusFar_scala = '''\n\nprintln(\"The number of scala points you have accumulated thus far is  \" + cumPoints +\" out of \"+ cumMaxPoints)'''
            cumThusFar_python = '''\n\nprint(\"The number of python points you have accumulated thus far is  \"+str(cumPoints) +\" out of \"+str(cumMaxPoints))'''
            prob_score_python_str = prob_score_python_str + cumThusFar_python
            prob_score_scala_str = prob_score_scala_str + cumThusFar_scala
            # initialize 2 cumulative cells, one for python, the other for scala
            # >> initialize cell for python > add metadata > "TEST_Cell_Initializer_or_Total": True > Used in ExtractResult > if True, skip concat stdOutString
            # >> initialize cell for scala > add metadata > "TEST_Cell_Initialize_or_Total": True > Used in ExtractResult > if True, skip concat stdOutString
            initCell_python = json.loads(newCell_str)
            initCell_scala = json.loads(newCell_str)

            initCell_python['command'] = '''%python\ncumPoints = 0\ncumMaxPoints = 0'''
            initCell_scala['command'] = '''%scala\nvar cumPoints = 0\nvar cumMaxPoints = 0'''


            initCell_python['metadata']['TEST_Cell_Initialize_or_Total'] = True
            initCell_scala['metadata']['TEST_Cell_Initialize_or_Total'] = True
        
            initCell_python['metadata']['lx_test_only'] = True
            initCell_scala['metadata']['lx_test_only'] = True

            first_TEST_Cells_position = assignmentsWithTest[0].TEST_Cells[0]['position']
            initCell_python['position'] = first_TEST_Cells_position - 0.7 # << set the position to before the first TEST cell
            initCell_scala['position'] = first_TEST_Cells_position - 0.3 # << set the position to before the first TEST cell

            tests.append(Assignment(PROBLEM_Cells=[],
                                    SOLUTION_Cells=[],
                                    Test_Cells=[],
                                    TEST_Cells=[initCell_python],
                                    problem_points = 0))
            
            tests.append(Assignment(PROBLEM_Cells=[],
                                    SOLUTION_Cells=[],
                                    Test_Cells=[],
                                    TEST_Cells=[initCell_scala],
                                    problem_points = 0))

         
            # loop through each TEST cell
            for assignment in assignmentsWithTest:
                testCells = assignment.TEST_Cells.copy() # [{...TEST Cell...}]
                assert len(testCells) == 1, "There can be only one TEST cell!"

                newCell = json.loads(newCell_str)
                newCell['command'] = testCells[0]['command']
                newCell['metadata'] = testCells[0]['metadata']
                newCell['metadata']['lx_test_only'] = "True"
                newCell['metadata']['TEST_Cell_Initialize_or_Total'] = "False" # >> will be put into stdOutString in extractResult
                newCell['position'] = testCells[0]['position']

                x = 0
                command = newCell['command'].split("\n")
                while command[x] in ["", " ", "  ", "   "]: # just in case there is a space or new line before magic cell.
                    x += 1
                    
                header = command[x]

                matchObj = re.match(r"^%(\w+)\s*$", header, re.UNICODE)
                if matchObj:
                    magic_lang = matchObj.group(1) #python, scala
                    if x+1 < len(command):
                        content = "\n".join(command[x+1:]) #command without magic cell << var local_points is in the content
                    else:
                        content = ""

                    if magic_lang == "python": # header = %python, %scala
                        firstCellSource=header+'''\nmaxPoints={}\n\n'''.format(assignment.problem_points)+content+counter_str+prob_score_python_str
                    elif magic_lang == "scala":
                        firstCellSource=header+'''\nvar maxPoints={}\n\n'''.format(assignment.problem_points)+content+counter_str+prob_score_scala_str
                    else:
                        print("Language in the cell not supported. So this cell cannot be run and skipped.")
                        firstCellSource=header+"\n"+content

                else: # if no header, check notebook language
                    firstCellSource = newCell['command']

                    if notebook_default_langauge == "python": # python notebook, so the def lang is %python (where some cells can be %scala)
                        # add py counter    
                        firstCellSource='''%python\nmaxPoints={}\n\n'''.format(assignment.problem_points)+firstCellSource+counter_str+prob_score_python_str
                    elif notebook_default_langauge == "scala": # scala notebook, so the def lang is %scala (where some cells can be %python)
                        # add scala counter
                        firstCellSource='''%scala\nvar maxPoints={}\n\n'''.format(assignment.problem_points)+firstCellSource+counter_str+prob_score_scala_str

                newCell['command'] = firstCellSource
                testCells[0] = newCell

                tests.append(Assignment(PROBLEM_Cells=[],
                                        SOLUTION_Cells=[],
                                        Test_Cells=[],
                                        TEST_Cells=testCells,
                                        problem_points = assignment.problem_points))
            
            # ## sum
            # >> add sum cell for python > add metadata > "TEST_Cell_Initializer_or_Total": True > Used in ExtractResult > if True, skip concat stdOutString >> grab
            # >> add sum cell for scala > add metadata > "TEST_Cell_Initializer_or_Total": True > Used in ExtractResult > if True, skip concat stdOutString >> grab

            # total cells for python and scala
            totalCell_python = json.loads(newCell_str)
            totalCell_scala = json.loads(newCell_str)

            totalCell_python['command'] = '''%python\nprint(\"\\nThe number of points you have scored in total for all Problems in Python is \"+ str(cumPoints)+\" out of \"+ str(cumMaxPoints))'''
            totalCell_scala['command'] = '''%scala\nprintln(\"\\nThe number of points you have scored in total for all Problems in Scala is \"+ cumPoints+\" out of \"+cumMaxPoints)'''

            totalCell_python['metadata']['TEST_Cell_Initialize_or_Total'] = True
            totalCell_scala['metadata']['TEST_Cell_Initialize_or_Total'] = True
            
            totalCell_python['metadata']['lx_test_only'] = True
            totalCell_scala['metadata']['lx_test_only'] = True

            totalCell_python['metadata']['lx_python_score_in_total'] = True
            totalCell_scala['metadata']['lx_scala_score_in_total'] = True

            totalCell_python['metadata']['deletable'] = False
            totalCell_scala['metadata']['deletable'] = False

            
            last_TEST_Cells_position = tests[-1].TEST_Cells[0]['position']
            totalCell_python['position'] = last_TEST_Cells_position + 1 # << set the position to after the last TEST cell
            totalCell_scala['position'] = last_TEST_Cells_position + 2 # << set the position to after the last TEST cell


            tests.append(Assignment(PROBLEM_Cells=[],
                                    SOLUTION_Cells=[],
                                    Test_Cells=[],
                                    TEST_Cells=[totalCell_python], #TEST_Cells=l1, 
                                    problem_points = 0))
            
            tests.append(Assignment(PROBLEM_Cells=[],
                                    SOLUTION_Cells=[],
                                    Test_Cells=[],
                                    TEST_Cells=[totalCell_scala], #TEST_Cells=l2, 
                                    problem_points = 0))
            
            # sum of totalCell_python and totalCell_scala
            # XXXXXXXXXX = totScore >> to be filled in by extractResult after graded
            # YYYYYYYYYY = posScore >> to be filled in by extractResult after graded         
            totalCell = json.loads(newCell_str)
            totalCell['command'] = '''%md\nThe number of points you have scored in total for this entire set of Problems is XXXXXXXXXX out of YYYYYYYYYY.'''
            totalCell['metadata']['TEST_Cell_Initialize_or_Total'] = True
            totalCell['metadata']['lx_test_only'] = True
            totalCell['position'] = last_TEST_Cells_position + 3

            tests.append(Assignment(PROBLEM_Cells=[],
                                    SOLUTION_Cells=[],
                                    Test_Cells=[],
                                    TEST_Cells=[totalCell],
                                    problem_points = 0))

            returnNB = DBAssignmentNotebook()
            returnNB.assignments = tests[:2] + self.assignments + tests[2:len(tests)]
            returnNB.courseDetails = self.courseDetails
            returnNB.assignmentNumber = self.assignmentNumber
            returnNB.header = self.header

            return returnNB
        else:
            print("Notebook type not supported.")
            returnNB = DBAssignmentNotebook()
            returnNB.assignments = tests[:2] + self.assignments + tests[2:len(tests)]
            returnNB.courseDetails = self.courseDetails
            returnNB.header = self.header
            return returnNB #return empty assignment notebook
   
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
        finalGradesDict = {'lx_problem_total_scored_points':0, 'lx_problem_total_possible_points':0}
        stdOutString = ''


        for assignment in self.assignments:
            if assignment.amITEST():
                # Extract the data from this test
                if "command" in assignment.TEST_Cells[0]: # dbc <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
                    has_result_s = False  
                    C = assignment.TEST_Cells[0] # dict of a cell  
                    if assignment.TEST_Cells[0]['results'] != None:
                        if "data" in assignment.TEST_Cells[0]['results']:
                            if isinstance(assignment.TEST_Cells[0]['results']['data'], list): # if data is list << actually for python
                                if len(assignment.TEST_Cells[0]['results']['data']) > 0: 
                                    if "data" in assignment.TEST_Cells[0]['results']['data'][0]:
                                        s = assignment.TEST_Cells[0]['results']['data'][0]['data'] # text output

                                        matchObj = re.match(r'^<div class=\"ansiout\">(.+)</div>$', s, flags=re.M | re.DOTALL | re.UNICODE)
                                        if matchObj:
                                            has_result_s = True # there is output
                                            s=str(matchObj.group(1)) # e.g. >> x is incorrect !\nThe number of points you have scored for this problem is 1 out of 3\n\n
                                        
                            elif(isinstance(assignment.TEST_Cells[0]['results']['data'], str)): # if data is string << actually for scala
                                
                                s = assignment.TEST_Cells[0]['results']['data'] # text output
                                matchObj = re.match(r'^<div class=\"ansiout\">(.+)</div>$', s, flags=re.M | re.DOTALL | re.UNICODE)
                                #has_result_s = True # there is output
                                if matchObj:
                                    has_result_s = True # there is output
                                    s=str(matchObj.group(1)) # e.g. >> x is incorrect !\nThe number of points you have scored for this problem is 1 out of 3\n\nmaxPoints: Int = 1 ...

                                    matchObj2 = re.match(r'^(.*The number of points you have scored for this problem is \d+ out of \d+).*$', s, flags=re.M | re.DOTALL | re.UNICODE)
                                    if matchObj2:
                                        s=str(matchObj2.group(1))
  
                    else:
                        s = "Command skipped, 0 out of "  + str(assignment.problem_points) + " were given."
                    if not has_result_s: # if there is output
                        matchObj = re.match(r"^.*((?://|#)\s+ASSIGNMENT\s+\d+,\s+TEST\s+\d+,\s+Points\s+\d+).*$", C['command'], flags=re.M | re.DOTALL | re.UNICODE | re.I)

                    C = assignment.TEST_Cells[0] # dict of a cell
                    
                    matchObj = re.match(r"^.*((?://|#)\s+ASSIGNMENT\s+\d+,\s+TEST\s+\d+,\s+Points\s+\d+).*$", C['command'], flags=re.M | re.DOTALL | re.UNICODE | re.I)
                    if matchObj:
                    
                        C['command'] = matchObj.group(1)
                    metadata = C['metadata']
                    if metadata['TEST_Cell_Initialize_or_Total'] == "False": # We need only actual TEST cells. Not initializer at header or total score at footer.
                        md='''##TESTs for Problem {} of {} {} were run and their results are as follows:\n'''.format(metadata['lx_problem_number'], metadata['lx_assignment_type'], metadata['lx_assignment_number']) # for submission comment feedback on Studium                      
                        stdOutString += '''\n{}\n{}\n'''.format(md, s)
                                  
                else:
                    print("Notebook type not supported.")

        
   
        return finalGradesDict, stdOutString
    
    def getPlatformCellName(self,notebook):
        """
        return the platform specific names for the list of cells and the individual cells
        """
        return 'commands','command'

    
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

        Returns
        -------
        notebook : nbformat.NotebookNode
            the ready made assignment Notebook.
        '''
        
        assignmentName = "ASSIGNMENT_{}_{}".format(str(self.assignmentNumber), notebook_type)
        assignmentLanguage = notebook_language
        



        # This is a new dbc notebook.
        assignmentNotebook_0_str = '''{
            "version": "NotebookV1",
            "origId": 2391963185141844,
            "name": "'''
        assignmentNotebook_1_str = assignmentName
        assignmentNotebook_2_str = '''",
            "language": "'''
        assignmentNotebook_3_str = assignmentLanguage
        assignmentNotebook_4_str = '''",
            "commands": [],
            "dashboards": [],
            "guid": "084dd49f-abe6-4884-9398-93f1b0d98543",
            "globalVars": {},
            "iPythonMetadata": null,
            "inputWidgets": {},
            "notebookMetadata": {
                "pythonIndentUnit": 4,
                "lx":1
            }
        }'''

        assignmentNotebook_str = assignmentNotebook_0_str +\
                                    assignmentNotebook_1_str +\
                                    assignmentNotebook_2_str +\
                                    assignmentNotebook_3_str +\
                                    assignmentNotebook_4_str

        assignmentNotebook = json.loads(assignmentNotebook_str)
        assignmentNotebook = self._add_course_metadata(assignmentNotebook,'notebookMetadata')
        assignmentNotebook = self._add_assignment_metadata(assignmentNotebook)
        assignmentNotebook = self._add_header(assignmentNotebook,is_dbc=True)

        for assignment in self.assignments:
            if ('problem' in notebook_type):
                # Add problem + Test
                assignmentNotebook['commands'] += assignment.PROBLEM_Cells # append all items (cell dict) in a list to the other list
                assignmentNotebook['commands'] += assignment.Test_Cells
            if ('solution' in notebook_type):
                assignmentNotebook['commands'] += assignment.SOLUTION_Cells
            if ('TEST' in notebook_type):
                # Add TEST cells
                assignmentNotebook['commands'] += assignment.TEST_Cells

        # renumber position of cells in commands in assignmentNotebook
        if notebook_type=='grading_problem_solution_TEST':
            AssignmentNotebook.injectTestCells(assignmentNotebook,'commands')     

        new_index = 0
        for cell in assignmentNotebook['commands']:
            cell['position'] = new_index
            new_index += 1

        self.notebook = assignmentNotebook

        return self.notebook # as json dict

    def nb_as_json(self,notebook_language):
        '''
        Creates a json string of the notebook.
        '''
        return self.to_notebook(notebook_language=notebook_language,notebook_type="grading_problem_solution_TEST")


class DBCourseDetails(CourseDetails):
    """
    The specific details regarding the Intro to Data Science.
    All the specifics are to be put inside the config.json inside the package

    What needs to be specified in the config.json are the following
    {
      "master_notebooks":["00","01","02","03","04","05","06","07",
                          "08","09","10","11","12","13","14","15",
                          "16","17","18"],
      "notebook_folder":"../master/jp",
      "target_notebook_folder":"lectures",
      "target_notebook_book_folder":"book/Notebooks",
      "assignments":[1,2,3,4,5],
      "CourseID":"1MS041",
      "CourseName":"Introduction to Data Science: A Comp-Math-Stat Approach",
      "CourseInstance":"2020"
    }
    """
    def __init__(self):
        import json
        import pkg_resources

        resource_package = __name__
        resource_path = '../../configNotebooks.json'

        with pkg_resources.resource_stream(resource_package, resource_path) as f:
            courseDetailsDict = json.load(f)
        super().__init__(courseDetailsDict)
        




class DBLectureNotebook(DBCourseNotebook):
    def __init__(self,nb_filename=None):
        self.courseDetails = DBCourseDetails()

        self.header = '''# {}, Year {} ({})\n### ScaDaMaLe Course [Site](https://lamastex.github.io/scalable-data-science/sds/3/x/) and [book](https://lamastex.github.io/ScaDaMaLe/index.html) \
    \n{} Raazesh Sainudiin. [Attribution 4.0 International \
    (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)''' \
    .format(self.courseDetails['CourseName'],
            self.courseDetails['CourseInstance'],
            self.courseDetails['CourseID'],
            self.courseDetails['CourseInstance'],
            self.courseDetails['CourseInstance'])
        super().__init__(nb_filename=nb_filename, courseDetails=self.courseDetails, header=self.header)



    def _parse_notebook(self):
        """
            This function parses the raw notebook and does the following
            * Identifies all assignment cells and tags them with correct metadata
            * Prepares the assignment cells for student version
            * Appends on that by inserting assignment cells with generic instructions
            * Stores all tagged and prepared assignment cells in self.assignmentCells
            * Inserts / replaces the cells in the self.notebook with the tagged
                and prepared cells
        """
        # Prepare the metadata for the assignment cells and put them in the cell metadata
        # take master NB and turn the #PROBLEM x, #POINT y, #TEST x into md cells
        #    ADD PROBLEM number in cell metadata
        #    TODO? make dictionary of points scored, etc.

        # -----------------------------------------------------------------------------------------
        # parse dbc
        
        print("Parsing dbc notebook")

        cellIndex=-1
        AssnProbSolDict={}
        indicesToInsertCells=[]

        # commands with unsorted positions of cells
        commands = self.notebook['commands'] # list of cells. each cell is dict. (list of dict)

        # from this point, commands are sorted by position
        # sort cells in commands by position
        commands = sorted(commands, key=lambda cell: cell['position'], reverse=False)

        for cell in commands: # loop through each cell (already sorted by postion) in commands
            cellIndex=cellIndex+1
            
            source = cell['command']
            source_lines = source.split('\n')

            first_line = source_lines[0] # first line
            matchObj_magic = re.match(r'%(\w+)', first_line, re.U) # %scala, %r, %python, etc.
            if matchObj_magic:
                magic_line = first_line+"\n"
                
                x=1
                while(source_lines[x]==''): # skip blank lines
                    x += 1
                header_line = source_lines[x] 

                content = ""
                if(x+1 < len(source_lines)):
                    content = '\n'.join(source_lines[x+1:]) # after header_line until the end # gives '' if no extra lines are there

            else:
                magic_line = ""
                header_line = first_line # = source_lines[0] # maybe or maybe not a header

                content = ""
                if(len(source_lines)>=2):
                    content = '\n'.join(source_lines[1:]) # second line until the end # gives '' if no extra lines are there
            
            # Example matches (starting exactly with # or //)
            # # Assignment 1, Problem 2, Points 3
            # // Assignment 1, Problem 2, Points 3
            matchObj = re.match(r'^(?:#|//)\s*(\w+)\s+(\w+),\s*(\w+)\s+(\d+),\s*(\w+)\s*(\d+)', header_line, re.U)

            if matchObj:

                # group 1 - ASSIGNMENT, or EXAM
                assignmentType = str(matchObj.group(1)) # ASSIGNMENT
                if assignmentType=='ASSIGNMENT':
                    assignmentType2Print='Assignment'
                else:
                    assignmentType2Print='Exam'

                # group 2 - Assignment Number
                assignmentNum = str(matchObj.group(2))

                try:
                    if (int(assignmentNum) not in self.assignmentNumbers):
                        self.assignmentNumbers.append(int(assignmentNum))
                except ValueError as e:
                    if (assignmentNum not in self.assignmentNumbers):
                        self.assignmentNumbers.append(assignmentNum)

                # group 3 - PROBLEM, SOLUTION, Test or TEST
                cell_type = matchObj.group(3) 

                # group 4 - Problem Number
                probNum=str(int(matchObj.group(4))) 

                # group 5 is just a string 'Points', so we skip this.

                # group 6 - Problem Points
                probPoints=str(int(matchObj.group(6))) 

                # dbc json uses the same name for cell metadata, and also exactly at the same level, so no need to change anything here.
                cell['metadata']['lx_assignment_type']=assignmentType
                cell['metadata']['lx_assignment_type2print']=assignmentType2Print
                cell['metadata']['lx_assignment_number']=assignmentNum
                cell['metadata']['lx_problem_cell_type']=cell_type
                cell['metadata']['lx_problem_number']=probNum
                cell['metadata']['lx_problem_points']=probPoints
                cell['metadata']['deletable']=False # this is to make sure cells of this type are non-deletable

                if (cell_type == 'PROBLEM' or cell_type == 'SOLUTION' or cell_type == 'Test'):
                    cell['command'] = magic_line+content # remove header line comment. keep the magic_line if exist. <<<<
                    if assignmentNum+'_'+probNum+'_'+cell_type not in AssnProbSolDict:
                        if(cell_type != 'Test'):
                            #md='''---\\n## Assignment {}, {} {}\\nMaximum Points = {}'''.format(assignmentNum,LX_Prob_CellType,probNum,probPoints)
                            md='''---\\n## {} {}, {} {}\\nMaximum Points = {}'''.format(assignmentType2Print,assignmentNum,cell_type,probNum,probPoints)
                        else:
                            md='''---\\n#### Local {} for {} {}, PROBLEM {}\\nEvaluate cell below to make sure your answer is valid. You **should not** modify anything in the cell below when evaluating it to do a local test of your solution.\\nYou may need to include and evaluate code snippets from lecture notebooks in cells above to make the local test work correctly sometimes (see error messages for clues). This is meant to help you become efficient at recalling materials covered in lectures that relate to this problem. Such local tests will generally not be available in the exam.'''.format(cell_type,assignmentType2Print,assignmentNum,probNum)

                        
                        # newCell with position = -1. To be renumbered later in the code.
                        newCell_0_str = '''{
                            "version": "CommandV1",
                            "origId": 2391963185141926,
                            "guid": "f21055aa-ee56-4536-9eb6-d9752d5821b6",
                            "subtype": "command",
                            "commandType": "auto",
                            "position": -1,
                            "command": "%md\\n'''
                        newCell_1_str = md
                        newCell_2_str = '''",
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

                        newCell_str = newCell_0_str + newCell_1_str + newCell_2_str

                        newCell = json.loads(newCell_str) # newCell as dict
                        newCell['metadata'] = cell['metadata']

                        indicesToInsertCells.append([cellIndex,newCell])
                        self.assignmentCells.append(newCell)
                        cellIndex=cellIndex+1
                        AssnProbSolDict[assignmentNum+'_'+probNum+'_'+cell_type]=1
                        
                self.assignmentCells.append(cell)

        # renumber self.assignmentCells << list of cell and newCell as dict (only those that match header and only for cell_type = PROBLEM, SOL, Test)
        new_index = 0
        for cell in self.assignmentCells:
            cell['position'] = new_index
            new_index += 1

        # now insert the md cells at the right places
        for iC in indicesToInsertCells:
            commands.insert(iC[0],iC[1]) # We get self.notebook['commands'] as list of dict!

        # renumber commands
        new_index = 0
        for cell in commands:
            cell['position'] = new_index
            new_index += 1

        # put commands back to self.notebook
        self.notebook['commands'] = commands

class DBCourse():
    """
    Wrapper for the entire course. All details are in IDSCourseDetails.

    Parameters
    ----------
    courseDetails : IDSCourseDetails
    lectureNotebooks : dict('notebook_filename' : IDSLectureNotebook)
        a dictionary of key,value being notebook filename and an IDSLectureNotebook
    assignments : dict('assignment number' : IDSAssignmentNotebook)
        a dictionary of key,value being assingment number and IDSAssignmentNotebook

    Methods
    -------
    makeAssignmentNotebook(assignment_number,notebook_type='problem_solution_TEST')
        creates the AssignmentNotebook related to assignment_number of the specified
        notebook_type
    to_nb()
        makes a lecture notebook out of all notebooks described in IDSCourseDetails.
    """
    def __init__(self):
        self.courseDetails = DBCourseDetails()
        self.lectureNotebooks = self._load_notebooks()
        self.assignments = self._create_assignments()
        

    def _load_notebooks(self):
        notebooks = {}

        #load dbc master notebooks from notebook_folder='master/dbc'
        print("load dbc master notebooks")
        for nb_name in self.courseDetails['master_notebooks']: #nb_name = 00, 01, 02, ...
            notebooks[nb_name]=DBLectureNotebook(self.courseDetails['notebook_folder']+"/" + nb_name + ".dbc")
        


        return notebooks
    

    def _create_assignments(self):
        assignments = {}
        for assignment_number in self.courseDetails['assignments']:
            assignments[assignment_number]=DBAssignmentNotebook(courseNotebooks=self.lectureNotebooks.values(),
                                                                 assignmentNumber = assignment_number)
        return assignments


    def makeAssignmentNotebook(self,assignment_number,notebook_type='problem_solution_TEST'):

        # self.assignments = {"1":"...IDSAssignmentNotebook Object...", "2":"...IDSAssignmentNotebook Object...", ...}
        # assignment = IDSAssignmentNotebook Object
        assignment = self.assignments[assignment_number] 
        target_path = self.courseDetails['target_notebook_folder'] # lectures

        # Just to check the extension of the source file inside .dbc
        # .scala, .py, .r, etc.
        with ZipFile(self.courseDetails['notebook_folder']+"/"+self.courseDetails['master_notebooks'][0]+".dbc", 'r') as zipObj: # nb_filename is a full path to .dbc file ! not just a file name !
            # Unzip .dbc into the same directory, yielding a file in .scala, .py, etc., in which the content is in a json format !
            namelist_in_zip = [file_name for file_name in zipObj.namelist() if file_name.split(".")[-1] not in ["mf"]]

            if len(namelist_in_zip) == 1 :
                source_file_name = namelist_in_zip[0]
                file_extension = source_file_name.split(".")[-1]
            else:
                print("No file matched. Return None.")
                return None # return empty dict << may raise error at a later point

        # write with an original extension file first and zip it in .dbc ! <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
        # type(assignment) = IDSAssignmentNotebook Object
        # to_nb in the following line is in AssignmentNotebook.py, class AssignmentNotebook
        assignment.to_nb(target_path+"/"+"Assignment_%d_%s.%s" % (assignment_number,notebook_type,file_extension),notebook_type) #<< call to_nb in AssignmentNotebook.py, in class AssignmentNotebook // not to_nb below !

    
    def to_nb(self):
    # Called from generate.py, line 12, course.to_nb()
        target_path = self.courseDetails['target_notebook_folder']

        # Just to check the extension of the source file inside .dbc
        # .scala, .py, .r, etc.
        with ZipFile(self.courseDetails['notebook_folder']+"/"+self.courseDetails['master_notebooks'][0]+".dbc", 'r') as zipObj: # nb_filename is a full path to .db file ! not just a file name !
            # Unzip .dbc into the same directory, yielding a file in .scala, .py, etc., in which the content is in a json format !
            namelist_in_zip = [file_name for file_name in zipObj.namelist() if file_name.split(".")[-1] not in ["mf"]]

            if len(namelist_in_zip) == 1 :
                source_file_name = namelist_in_zip[0]
                file_extension = source_file_name.split(".")[-1]
            else:
                print("No file matched. Return None.")
                return None # return empty dict << may raise error at a later point

        for nb_name in self.lectureNotebooks:
            notebook = self.lectureNotebooks[nb_name]
            notebook.to_nb(target_path+'/' + nb_name + '.' + file_extension, skipAssignments=True)



