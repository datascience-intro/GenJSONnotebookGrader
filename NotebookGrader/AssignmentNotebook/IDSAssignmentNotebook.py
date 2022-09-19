#from .AssignmentNotebook import *
from .AssignmentNotebook import *


class IDSCourseNotebook(CourseNotebook):
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


    self.meta = 'metadata'
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
    def __init__(self,nb_filename=None, examHeader='', courseDetails=None, header=''):
        self.cellNameForMetadata = "metadata"
        self.cellName = "cells"
        super().__init__(nb_filename, examHeader, courseDetails, header)
        # if (nb_filename != None):
        #     self.notebook = self._from_file(nb_filename)
        #     self.nb_filename = nb_filename
        #     self._parse_notebook()
        # else: self.notebook=None



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
        with open(nb_filename,mode='r') as f:
            nb = nbformat.read(f,as_version=4)
        return nb
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
        with open(target_filename,mode='w') as f:
            nbformat.write(self.toLectureNotebook(skipAssignments),f)


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
        print("Parsing Jupyter notebook")

        cellIndex=-1
        AssnProbSolDict={}
        indicesToInsertCells=[]
        for cell in self.notebook['cells']:
            cellIndex=cellIndex+1
            source = cell['source']
            source_lines = source.split('\n')
            header_line = source_lines[0] # first line
            content = '\n'.join(source_lines[1:]) # gives '' if no extra lines are there
            matchObj = re.match(r'#\s*(\w+)\s+(\w+),\s*(\w+)\s+(\d+),\s*(\w+)\s*(\d+)', header_line, re.U)
            if matchObj:
                assignmentType = str(matchObj.group(1)) # ASSIGNMENT
                if assignmentType=='ASSIGNMENT':
                    assignmentType2Print='Assignment'
                else:
                    assignmentType2Print='Exam'
                assignmentNum = str(matchObj.group(2))

                try:
                    if (int(assignmentNum) not in self.assignmentNumbers):
                        self.assignmentNumbers.append(int(assignmentNum))
                except ValueError as e:
                    if (assignmentNum not in self.assignmentNumbers):
                        self.assignmentNumbers.append(assignmentNum)

                cell_type = matchObj.group(3) # Problem, Solution, Test or TEST
                probNum=str(int(matchObj.group(4)))
                probPoints=str(int(matchObj.group(6)))
                cell['metadata']['lx_assignment_type']=assignmentType
                cell['metadata']['lx_assignment_type2print']=assignmentType2Print
                cell['metadata']['lx_assignment_number']=assignmentNum
                cell['metadata']['lx_problem_cell_type']=cell_type
                cell['metadata']['lx_problem_number']=probNum
                cell['metadata']['lx_problem_points']=probPoints
                cell['metadata']['deletable']=False # this is to make sure cells of this type are non-deletable
                if (cell_type == 'PROBLEM' or cell_type == 'SOLUTION' or cell_type == 'Test'):
                    cell['source'] = content # remove first comment line containing PROBLEM
                    if assignmentNum+'_'+probNum+'_'+cell_type not in AssnProbSolDict:
                        if(cell_type != 'Test'):
                            #md='''---\n## Assignment {}, {} {}\nMaximum Points = {}'''.format(assignmentNum,LX_Prob_CellType,probNum,probPoints)
                            md='''---\n## {} {}, {} {}\nMaximum Points = {}'''.format(assignmentType2Print,assignmentNum,cell_type,probNum,probPoints)
                        else:
                            md='''---\n#### Local {} for {} {}, PROBLEM {}\nEvaluate cell below to make sure your answer is valid. \
                            You **should not** modify anything in the cell below when evaluating it to do a local test of \
                            your solution.\nYou may need to include and evaluate code snippets from lecture notebooks in cells above to make the local test work correctly sometimes (see error messages for clues). This is meant to help you become efficient at recalling materials covered in lectures that relate to this problem. Such local tests will generally not be available in the exam.'''.format(cell_type,assignmentType2Print,assignmentNum,probNum)
                        newCell = nbformat.v4.new_markdown_cell(md)
                        newCell['metadata'] = cell['metadata']
                        indicesToInsertCells.append([cellIndex,newCell])
                        self.assignmentCells.append(newCell)
                        cellIndex=cellIndex+1
                        AssnProbSolDict[assignmentNum+'_'+probNum+'_'+cell_type]=1
                self.assignmentCells.append(cell)

        # now insert the md cells at the right places
        for iC in indicesToInsertCells:
            self.notebook['cells'].insert(iC[0],iC[1])

class IDSAssignmentNotebook(AssignmentNotebook):
    """
    Represents an assignmentNotebook for Introduction to Data Science (IDS)
    Extends on AssignmentNotebook but has some extra bells and whistles.

    * The difference being that you can initialize empy
    * initialize from a file
    * initialize from a notebook
    """
    #this init is for now identical in both classes. maybe create a second init or add it to super init.
    def __init__(self,courseNotebooks = None,assignmentNumber = 1,nb_filename=None, notebook=None):
        self.notebook = None
        self.cellNameForMetadata = "metadata"
        self.cellName = "cells"

        if (nb_filename != None): # called from AutoGrader.py > prepareNotebookForGrading
            self.notebook = self._load_notebook(nb_filename) #<< Done
            self.courseDetails, self.assignmentNumber = self._extractCourseDetails(self.notebook) #<< Done
            #print(self.courseDetails)
            #print(IDSCourseDetails())
            assert self.courseDetails == IDSCourseDetails() # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
            self.header = self._extractHeader(self.notebook) #<< Done
            self.assignments = self._extractProblems(self.notebook) #<< Done
        elif courseNotebooks != None:
            self.courseDetails = IDSCourseDetails()
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
            self.courseDetails = IDSCourseDetails()
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
        if "source" in assignmentsWithTest[0].TEST_Cells[0]: #<< Use this if the line below doesn't work  << swtich0
            assignments = self.assignments
            numAssignments = len(assignmentNotebook.assignments)

            cumPointsInitializer = '''\ncumPoints=0; cumMaxPoints=0 # initialising the cummulative & cumMax points\n'''
            cumPointsCounter = ('''\ncumPoints=cumPoints+local_points\ncumMaxPoints=cumMaxPoints+maxPoints\n'''
                                '''print("The number of points you have scored for this problem is "+str(local_points)+" out of "+str(maxPoints))\n''')
            cumThusFar = '''\nprint("The number of points you have accumulated thus far is   "+str(cumPoints)+" out of "+str(cumMaxPoints))'''

            assignmentsWithTest = [assignment for assignment in assignmentNotebook.assignments if len(assignment.TEST_Cells) > 0]
            for index,assignment in enumerate(assignmentsWithTest):
                testCells = assignment.TEST_Cells.copy()
                assert len(testCells) == 1, "There can be only one TEST cell!"
                newCell = nbformat.v4.new_code_cell(testCells[0]['source'])
                newCell['metadata'] = testCells[0]['metadata']
                newCell['metadata']['lx_test_only'] = "True"
                firstCellSource = newCell['source']
                firstCellSource='''maxPoints={} # initialising the cummulative points\n'''.format(assignment.problem_points)+firstCellSource
                if (index == 0):
                    firstCellSource = firstCellSource+cumPointsInitializer+cumPointsCounter+cumThusFar
                elif (index == len(assignmentsWithTest)-1):
                    firstCellSource=firstCellSource+cumPointsCounter
                    firstCellSource=firstCellSource+'''\nprint(" ")'''*3
                    firstCellSource=firstCellSource+'''\nprint("The number of points you have scored in total for this entire set of Problems is "+str(cumPoints)+" out of "+str(cumMaxPoints))'''
                else:
                    firstCellSource=firstCellSource+cumPointsCounter+cumThusFar

                newCell['source'] = firstCellSource
                testCells[0] = newCell
                testAssignment = Assignment(PROBLEM_Cells=[],
                                        SOLUTION_Cells=[],
                                        Test_Cells=[],
                                        TEST_Cells=testCells,
                                        problem_points = assignment.problem_points)
                test_problem_nr = testAssignment.getProblemNumber()
                correct_problem_nr_assigment = [assignment for assignment in assignments if assignment.getProblemNumber() == test_problem_nr]
                assert(len(correct_problem_nr_assigment) == 1), "There can only be one assignment with problem_nr: %s" % test_problem_nr
                correct_problem_nr_assigment[0].TEST_Cells = testCells
                #print(correct_problem_nr_assigment[0])

            returnNB = IDSAssignmentNotebook()
            returnNB.assignments = assignments#+tests
            returnNB.courseDetails = self.courseDetails
            returnNB.assignmentNumber = self.assignmentNumber
            returnNB.header = self.header
            return returnNB

        # ---
        else:
            print("Notebook type not supported.")
            returnNB = AssignmentNotebook()
            returnNB.assignments = []
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
        totScore = 0
        posScore = 0


        for assignment in self.assignments:
            if assignment.amITEST():
                # Extract the data from this test
                if "source" in assignment.TEST_Cells[0]: # ipynb
                    if (len(assignment.TEST_Cells[0]['outputs']) > 0): # if there is output
                        C = assignment.TEST_Cells[0]
                        stdout_cell = [cell for cell in C['outputs'] if cell.get('name','') == "stdout"]
                        #s = C['outputs'][0]["text"]
                        s = stdout_cell[0]["text"]

                        matchObj = re.match(r"^.*((?://|#)\s+ASSIGNMENT\s+\d+,\s+TEST\s+\d+,\s+Points\s+\d+).*$", C['source'], flags=re.M | re.DOTALL | re.UNICODE | re.I)
                        if matchObj:
                            C['source'] = matchObj.group(1)

                        metadata = C['metadata']
                        md='''##TESTs for Problem {} of {} {} were run and their results are as follows:\n'''.format(metadata['lx_problem_number'],
                        metadata['lx_assignment_type'],metadata['lx_assignment_number'])
                        stdOutString += '\n'+md+'\n'+s+'\n'
                        sSplitByNewLines = s.split('\n')
                        ls = ''.join(sSplitByNewLines[0:])
                        # matchObj = re.match(r"^.*points you have scored in total for this entire set of Problems is\s+(\d+)\s+out of\s+(\d+).*$", ls, re.UNICODE)
                        matchObj = re.match(r"^.*points you have accumulated thus far is\s+(\d+)\s+out of\s+(\d+).*$", ls, re.UNICODE)
                        if matchObj:
                            totScore=str(matchObj.group(1))
                            posScore=str(matchObj.group(2))
                            finalGradesDict['lx_problem_total_scored_points']=totScore
                            finalGradesDict['lx_problem_total_possible_points']=posScore

                else:
                    print("Notebook type not supported.")



        return finalGradesDict, stdOutString

    def getPlatformCellName(self,notebook):
        """
        return the platform specific names for the list of cells and the individual cells
        """
        return 'cells','source'

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
        assignmentNotebook = nbformat.v4.new_notebook()

        assignmentNotebook = self._add_course_metadata(assignmentNotebook,"metadata")
        assignmentNotebook = self._add_assignment_metadata(assignmentNotebook)
        assignmentNotebook = self._add_header(assignmentNotebook)

        for assignment in self.assignments:
            if ('problem' in notebook_type):
                # Add problem + Test
                assignmentNotebook['cells'] += assignment.PROBLEM_Cells
                assignmentNotebook['cells'] += assignment.Test_Cells
            if ('solution' in notebook_type):
                # Add solution
                assignmentNotebook['cells'] += assignment.SOLUTION_Cells
            if ('TEST' in notebook_type):
                # Add TEST cells
                assignmentNotebook['cells'] += assignment.TEST_Cells

        if notebook_type=='grading_problem_TEST':
            AssignmentNotebook.injectTestCells(assignmentNotebook,'cells')


        self.notebook = assignmentNotebook
        return self.notebook # as NotebookNode

    def nb_as_json(self,notebook_language):
        '''
        Creates a json representation of the notebook.
        '''
        return nbformat.writes(self.to_notebook(notebook_language=notebook_language,notebook_type="grading_problem_TEST"))

class IDSExamNotebook(AssignmentNotebook):
    """
    Represents an assignmentNotebook for Introduction to Data Science (IDS)
    Extends on AssignmentNotebook but has some extra bells and whistles.

    * The difference being that you can initialize empy
    * initialize from a file
    * initialize from a notebook

    Methods:

    """
    def __init__(self,courseNotebooks = None,assignmentNumber = 1,nb_filename=None, notebook=None,examHeader=''):
        self.notebook = None

        if (nb_filename != None):
            self.notebook = self._load_notebook(nb_filename)
            self.courseDetails, self.assignmentNumber = self._extractCourseDetails(self.notebook)
            assert self.courseDetails == IDSCourseDetails()
            self.header = self._extractHeader(self.notebook)
            self.examHeader = examHeader
            self.assignments = self._extractProblems(self.notebook)
        elif courseNotebooks != None:
            self.courseDetails = IDSCourseDetails()
            self.assignmentNumber = assignmentNumber
            CourseID = self.courseDetails['CourseID']
            self.header = '''# Exam {} for Course {}\\nMake sure you pass the `# ... Test` cells and\\n submit your solution notebook in the corresponding assignment on the course website.'''.format(self.assignmentNumber,CourseID,CourseID,self.assignmentNumber)
            self.examHeader=examHeader

            super().__init__(courseNotebooks, assignmentNumber)
        elif (notebook!=None):
            self.notebook = notebook
            self.courseDetails, self.assignmentNumber = self._extractCourseDetails(self.notebook)
            self.header = self._extractHeader(self.notebook)
            self.assignments = self._extractProblems(self.notebook)
        else:
            self.courseDetails = IDSCourseDetails()
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
        assert(self.courseDetails == assignmentNotebook.courseDetails), "Assignment notebook courseDetails dont match"
        assignments = self.assignments

        cumPointsInitializer = '''\ncumPoints=0; cumMaxPoints=0 # initialising the cummulative & cumMax points\n'''
        cumPointsCounter = ('''\ncumPoints=cumPoints+local_points\ncumMaxPoints=cumMaxPoints+maxPoints\n'''
                            '''print("The number of points you have scored for this problem is "+str(local_points)+" out of "+str(maxPoints))\n''')
        cumThusFar = '''\nprint("The number of points you have accumulated thus far is   "+str(cumPoints)+" out of "+str(cumMaxPoints))'''

        assignmentsWithTest = [assignment for assignment in assignmentNotebook.assignments if len(assignment.TEST_Cells) > 0]
        for index,assignment in enumerate(assignmentsWithTest):
            testCells = assignment.TEST_Cells.copy()
            assert len(testCells) == 1, "There can be only one TEST cell!"
            newCell = nbformat.v4.new_code_cell(testCells[0]['source'])
            newCell['metadata'] = testCells[0]['metadata']
            newCell['metadata']['lx_test_only'] = "True"
            firstCellSource = newCell['source']
            firstCellSource='''maxPoints={} # initialising the cummulative points\n'''.format(assignment.problem_points)+firstCellSource
            if (index == 0):
                firstCellSource = firstCellSource+cumPointsInitializer+cumPointsCounter+cumThusFar
            elif (index == len(assignmentsWithTest)-1):
                firstCellSource=firstCellSource+cumPointsCounter
                firstCellSource=firstCellSource+'''\nprint(" ")'''*3
                firstCellSource=firstCellSource+'''\nprint("The number of points you have scored in total for this entire set of Problems is "+str(cumPoints)+" out of "+str(cumMaxPoints))'''
            else:
                firstCellSource=firstCellSource+cumPointsCounter+cumThusFar

            newCell['source'] = firstCellSource
            testCells[0] = newCell
            testAssignment = Assignment(PROBLEM_Cells=[],
                                    SOLUTION_Cells=[],
                                    Test_Cells=[],
                                    TEST_Cells=testCells,
                                    problem_points = assignment.problem_points)
            test_problem_nr = testAssignment.getProblemNumber()
            correct_problem_nr_assigment = [assignment for assignment in assignments if assignment.getProblemNumber() == test_problem_nr]
            assert(len(correct_problem_nr_assigment) == 1), "There can only be one assignment with problem_nr: %s" % test_problem_nr
            correct_problem_nr_assigment[0].TEST_Cells = testCells

        returnNB = IDSExamNotebook(notebook=self.notebook,examHeader=self.examHeader)
        returnNB.assignments = assignments#+tests
        returnNB.courseDetails = self.courseDetails
        returnNB.assignmentNumber = self.assignmentNumber
        returnNB.header = self.header

        return returnNB

    def _extractProblems(self,notebook):

        # The lx_problem_cell_types are
        # PROBLEM
        # Test
        # TEST
        # SOLUTION

        problems = {}
        problemNumber = '0'
        for cell in notebook['cells']:
            metadata = cell['metadata']
            source = cell['source']
            if ('lx_problem_number' in metadata):
                problemNumber = metadata['lx_problem_number']


                if (problemNumber not in problems):
                    problems[problemNumber] = {metadata['lx_problem_cell_type']:[cell],
                                               'lx_problem_points':metadata['lx_problem_points']}
                else:
                    if (metadata['lx_problem_cell_type'] not in problems[problemNumber]):
                        problems[problemNumber][metadata['lx_problem_cell_type']] = [cell]
                    else:
                        problems[problemNumber][metadata['lx_problem_cell_type']]+=[cell]
            elif (problemNumber != '0'):
                # This is a student created cell and is not part of the original
                # we will assume the student intended this cell to be there, so we will add it
                # to the current problem
                cell['metadata']['lx_problem_cell_type'] = "PROBLEM"
                metadata = cell['metadata']
                if (metadata['lx_problem_cell_type'] not in problems[problemNumber]):
                    problems[problemNumber][metadata['lx_problem_cell_type']] = [cell]
                else:
                    problems[problemNumber][metadata['lx_problem_cell_type']]+=[cell]


        assignments = []

        for problem in problems:
            PROBLEM_Cells = problems[problem].get('PROBLEM',[])
            Test_Cells = problems[problem].get('Test',[])
            SOLUTION_Cells = problems[problem].get('SOLUTION',[])
            TEST_Cells = problems[problem].get('TEST',[])
            problem_points = problems[problem]['lx_problem_points']
            assignments.append(Assignment(PROBLEM_Cells=PROBLEM_Cells,
                                          SOLUTION_Cells=SOLUTION_Cells,
                                          Test_Cells=Test_Cells,
                                          TEST_Cells=TEST_Cells,
                                          problem_points = problem_points))
        return assignments

    def _extractHeader(self,notebook):
        return [cell['source'] for cell in notebook['cells'][:2]]

    def _add_header(self,notebook):
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
            if (type(self.header) == list):
                newCell = nbformat.v4.new_markdown_cell(self.header[0])
                newCell['metadata']['deletable']=False
                notebook['cells'].insert(0,newCell)

                newCell = nbformat.v4.new_code_cell(self.header[1])
                newCell['metadata']['deletable']=False
                notebook['cells'].insert(2,newCell)
        except Exception as e:
            pass
        if (type(self.header) == str):
            newCell = nbformat.v4.new_markdown_cell(self.header)
            newCell['metadata']['deletable']=False
            notebook['cells'].insert(0,newCell)
        return notebook

    def verifyExamID(self):
        examID = self.extractVariable(self.header[1],'MyAnonymousExamID')
        if (examID != "XXX"):
            return True
        else:
            return False

    def getExamID(self):
        return self.extractVariable(self.header[1],'MyAnonymousExamID')

    def extractVariable(self,cell_source,variableName):
        import ast
        ast_cell = ast.parse(cell_source)
        if (len(ast_cell.body) >= 1):
            for line in ast_cell.body:
                if (type(line) == ast.Assign):
                    if (line.targets[0].id == variableName):
                        if (type(line.value.value) == int):
                            return line.value.n
                        elif(type(line.value.value) == str):
                            return line.value.s
        return None



class IDSCourseDetails(CourseDetails):
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
        # might put this is superclass
    def __init__(self):
        import json
        import pkg_resources
        resource_package = __name__
        resource_path = './../../configNotebooks.json'

        with pkg_resources.resource_stream(resource_package, resource_path) as f:
            courseDetailsDict = json.load(f)
        super().__init__(courseDetailsDict)

#class IDSLectureNotebook(CourseNotebook):
class IDSLectureNotebook(IDSCourseNotebook):
    def __init__(self,nb_filename=None):
        self.courseDetails = IDSCourseDetails()
        self.metadataName = "metadata"
        self.cellName = "cells"
        self.header = '''# {}, Year {} ({})\n### ScaDaMaLe Course [Site](https://lamastex.github.io/scalable-data-science/sds/3/x/) and [book](https://lamastex.github.io/ScaDaMaLe/index.html) \
    \n{} Raazesh Sainudiin. [Attribution 4.0 International \
    (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)''' \
    .format(self.courseDetails['CourseName'],
            self.courseDetails['CourseInstance'],
            self.courseDetails['CourseID'],
            self.courseDetails['CourseInstance'],
            self.courseDetails['CourseInstance'])
        super().__init__(nb_filename=nb_filename, courseDetails=self.courseDetails, header=self.header)


class IDSBookNotebook(CourseNotebook):
    def __init__(self,nb_filename=None):
        super().__init__(nb_filename)

        self.courseDetails = IDSCourseDetails()
        self.header = None

    def _bookify(self,line_bound=10):
        for cell in self.notebook['cells']:
            if (cell['cell_type'] == 'markdown'):
                # Find all lines that start with $$ and add an extra line before it
                source = cell['source']
                subbed = re.sub(r"(\$\$(?<=\$\$).*?(?=\$\$)\$\$)",r"\n\g<1>\n",source,flags=re.MULTILINE | re.DOTALL)
                cell['source'] = subbed
            elif (cell['cell_type'] == 'code'):
                if (len(cell['outputs']) > 0):
                    if (cell['outputs'][0].get('output_type',"") == 'stream'):
                        lines = cell['outputs'][0]['text'].split('\n')
                        if (len(lines) > line_bound):
                            cell['outputs'][0]['text'] = '\n'.join(lines[:line_bound]+['...'])
                    elif (cell['outputs'][0].get('output_type',"") == 'error'):
                        cell['outputs'][0]['traceback']=cell['outputs'][0]['traceback'][-1:]

class IDSCourse():
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
        self.courseDetails = IDSCourseDetails()
        self.lectureNotebooks = self._load_notebooks()
        self.assignments = self._create_assignments()


    def _load_notebooks(self):
        notebooks = {}
        #load Jupyter master notebooks from notebook_folder='master/jp'
        print("load Jupyter master notebooks")
        for nb_name in self.courseDetails['master_notebooks']: #nb_name = 00, 01, 02, ...
            notebooks[nb_name]=IDSLectureNotebook(self.courseDetails['notebook_folder']+"/" + nb_name + ".ipynb")


        return notebooks

    def _create_assignments(self):
        assignments = {}
        for assignment_number in self.courseDetails['assignments']:
            assignments[assignment_number]=IDSAssignmentNotebook(courseNotebooks=self.lectureNotebooks.values(),
                                                                 assignmentNumber = assignment_number)
        return assignments


    def makeAssignmentNotebook(self,assignment_number,notebook_type='problem_solution_TEST'):

        assignment = self.assignments[assignment_number] # {"1":"...IDSAssignmentNotebook Object...", "2":"...IDSAssignmentNotebook Object...", ...}
        target_path = self.courseDetails['target_notebook_folder'] # lectures
        assignment.to_nb(target_path+"/"+"Assignment_%d_%s.ipynb" % (assignment_number,notebook_type),notebook_type)


    # Called from generate.py, line 12, course.to_nb()
    def to_nb(self):
        target_path = self.courseDetails['target_notebook_folder']
        for nb_name in self.lectureNotebooks:
            notebook = self.lectureNotebooks[nb_name]
            notebook.to_nb(target_path+'/' + nb_name + '.ipynb',skipAssignments=True)



class IDSBook():
    def __init__(self):
        self.courseDetails = IDSCourseDetails()
        self.lectureNotebooks = self._load_notebooks()
        self.assignments = self._create_assignments()

    def _load_notebooks(self):
        notebooks = {}
        for nb_name in self.courseDetails['master_notebooks']:
            notebooks[nb_name]=IDSBookNotebook(self.courseDetails['notebook_folder']+"/" + nb_name + ".ipynb")
        return notebooks

    def _create_assignments(self):
        assignments = {}
        for assignment_number in self.courseDetails['assignments']:
            assignments[assignment_number]=IDSAssignmentNotebook(courseNotebooks=self.lectureNotebooks.values(),
                                                                 assignmentNumber = assignment_number)
        return assignments

    def makeAssignmentNotebook(self,assignment_number,notebook_type='problem_solution_TEST'):
        assignment = self.assignments[assignment_number]
        target_path = self.courseDetails['target_notebook_book_folder']
        assignment.to_nb(target_path+"/"+"Assignment_%d_%s.ipynb" % (assignment_number,notebook_type))

    def to_nb(self):
        target_path = self.courseDetails['target_notebook_book_folder']
        for nb_name in self.lectureNotebooks:
            notebook = self.lectureNotebooks[nb_name]
            notebook._bookify()
            notebook.to_nb(target_path+'/' + nb_name + '.ipynb',skipAssignments=True)
