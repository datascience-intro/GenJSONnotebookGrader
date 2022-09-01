## what has been changed
- DB and IDS have been split into two classes 
- Autograder is split to more DB or IDS specific-functions, so main file gets more generalized
- AutoGrader-bash related communication with databricks are now run through the python REST-api
- removing some comments
- Fixed bug where non-evaluated TEST-cells still show original code with answers
- TESTs are injected after every problem instead of last on the page
- remove path dependencies on AutoGrader-bash folder (will remove it now since using python API)
- test if everything is working with both python-dbc notebooks and python-jupyter notebooks
- code will not interrupt if grader is started while cluster is starting (REST code)
## TODO:
- lots of filepath-strings
- final test if everything is working with both python-dbc notebooks and python-jupyter notebooks
- some functions can still be generalized or added into their respective classes


## Prologue

- This is the branch of Generic Autograder that can handle jupyter and databricks notebooks.
- It will have a small set of example notebooks and code to generate material
- Make sure you have generated the needed notebooks and that they are in the correct format, as described in [test_course repo](https://github.com/datascience-intro/test_course).


## Introduction

This AutoGrader supports:-
1. Jupyter Notebook (*.ipynb*) with Python and SageMath kernels.
2. databricks Notebook (*.dbc*) with Python, Scala and Spark kernels. This one supports Python and Scala languages in a single notebook.

## Platform-specific NotebookGrader
In the NotebookGrader package you can find the AutoGrader superclass with subclasses for IDS(jupyter) and Databricks AutoGraders.

## Notebook AutoGrader
### Pre-configured files and relevant pre-setup
For the grading of student submission notebooks, one has to pre-configure 3 files as follows:-

1. `configGrading.json`
This `configGrading.json` is the different file from the one used for the notebook extraction. One can find this file in `Autograder` directory. This file is mainly used to specify information needed for the system to grade student submission notebooks.

    	{
	    	"course" : 54514,
			"API_URL" : "https://uppsala.instructure.com",
			"API_KEY" : "1111111~XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
			"API_KEY_OWNER": "Suparerk Angkawattanwit",
			"Assignments" : [
			{
				"name": "ASSIGNMENT_1",
				"studium_id" : 0,
				"master_filename" : "Master/Assignment_1_problem_TEST.dbc",
				"start_date" : "2022-05-01",
				"end_date" : "2022-05-31"
			},
			{
				"name": "ASSIGNMENT_2",
				"studium_id" : 0,
				"master_filename" : "Master/Assignment_2_problem_TEST.dbc",
				"start_date" : "2022-06-01",
				"end_date" : "2022-06-30"
			}
			],
			"dbc_cluster_id": "9999-999999-xxxxxxxxxxxx",
			"dbc_cluster_name": "cluster-name"
			"dbc_workspace_dir" : /Users/email.com
    	}
	
	The description of each key in `configGrading.json` is in the table below:
	
	| Key | Description |
	|--|--|
	| course | Course ID on Studium. One can find it in the link in your browser's address bar. |
	|  API_URL | Link to Studium (or a link to Canvas Instructure used by your university) |
	| API_KEY | An API key to access Studium. You can create one in the setting menu on Studium |
	| API_KEY_OWNER | (optional) A name of the owner of the API key |
	| Assignments | A list of assignment names and grading periods |
	| name | Assignment name. This must be exactly the same one on Studium. If the system cannot find the name specified here on Studium, nothing is graded. |
	| studium_id | This always has to be set as 0, according to the documentation. |
	| master_filename | A path to an extracted notebook with problem and TEST cells |
	| start_date | A start date to grade the assignment. It starts at 00.01. |
	| end_date | An end date to grade the assignment, It ends at 23.59. |
	| dbc_cluster_id | An ID of a cluster on databricks used to execute student submission notebooks. |
	| dbc_cluster_name | (optional) A name of the cluster on databricks. |
	| dbc_workspace_dir| The databricks workspace of your choice. |
	
> **NOTE !**
> In case there are assignments with overlapped grading periods, the grading system will not start the next one until the current assignment's grading period ends. This means, practically, overlapped grading periods are not supported. However, if it is really necessary to have overlapped grading periods, one can work around by duplicating this set of codes (after extraction where extracted notebooks are present) and running the grading for two assignments separately.

2. `.databrickscfg`
	This `.databrickscfg`file is used by `databricks CLI` in the AutoGrader system to specify a databricks workspace where student submission notebooks are executed and graded. First of all, one needs to install databricks CLI, using the following command:-

	    pip install databricks-cli

	> Use an appropriate version of pip, e.g. pip3
	
	Next, to configure the`.databrickscfg` file, one can find it in the user home directory. Set a link to a databricks workspace where student submission notebooks are executed, along with its access token. One can create an access token in User Settings on databricks workspace. In the example below, one can find there is a default section where default databricks workspace used to execute is specified. The middle one is the alternative workspace just in case the default one is not working. The last one is again the default. It is specified here again just to show the name of the databricks workspace.

		[DEFAULT]
		host = https://uppsalauni-xxxxxx-xx-projects.cloud.databricks.com/
	    token = dapi11111111111111111111111111111111111
	    jobs-api-version = 2.1
		
	    [dbua-us-west]
	    host = https://dbc-123ca456-xxxx.cloud.databricks.com/?o=4444444444#
	    token = dapi222222222222222222222222222222222222
	    jobs-api-version = 2.1
       
	    [dbua-eu-west-1]
	    host = https://uppsalauni-xxxxxx-xx-projects.cloud.databricks.com/
	    token = dapi11111111111111111111111111111111111
	    jobs-api-version = 2.1
	    
3. `.netrc`
This `.netrc`is used when the system downloads graded student notebooks. The system uses `curl` command in a bash script to download the graded notebook from databricks where the access token is needed. Therefore, one also needs to specify the access token here in this file.

	    machine uppsalauni-xxxxxx-xx-projects.cloud.databricks.com
	    login token
	    password dapi11111111111111111111111111111111111
	
	    machine dbc-123ca456-xxxx.cloud.databricks.com/?o=4444444444#
	    login token
	    password dapi222222222222222222222222222222222222
	    
4.  The symbolic link named `Master`
Inside top directory of GenJSONnotebookGrader, there is a symbolic link named `Master`. This `Master` is linked to the directory where the extracted notebooks in the course are stored (e.g. `../test_course/GenerateMaterial/lectures`).  You can recreate the symbolic link to your liking:

	To remove the link, navigate to the top directory of this repo and:
		
		rm Master

	To create the link and then link it to the correct directory:
	

		ln -s ../<...YourCourseDirectory...>/GenerateMaterial/<...YourExtractedNotebookDirectory...>/ ./Master
	
	For example,
	
		rm Master
		ln -s ../Course_Repo/GenerateMaterial/lectures/ ./Master
	
> For the symbolic link, there is no restriction to name it just only `Master`. A different name for the link can be used. However, one has to change the path in `master_filename`  for each assignment in `configGrader.json` accordingly.

> In addition, one may decide to not use a symbolic link, but create an actual directory here instead, where TEST notebooks are copied and stored.

> The single dot (`.`) in the path means the current directory, while the double dots (`..`) means going up one level to its parent directory.

5. Build `sds-sagemath-autograde` image for the grading of Jupyter notebooks
Go into your course directory and run the following command:

	    docker build -t sds-sagemath-autograde:latest -f Dockerfile-sds-autograde .
	    
	Then, check if the image is built successfully by using the following command:-

	    docker images

	You will see `sds-sagemath-autograde` in the list of repository.

### Run AutoGrader
In the `GenJSONnotebookGrader` directory, run the following command:

    python3 Grader.py

- The autograder downloads the student submission notebooks from Studium and then grade them in the system. The points, comments (captured from TEST cells) and graded notebooks for student submissions (with commands in all TEST cells removed and left only with their cell results, preventing students from acessing the correct answers) will be uploaded to Studium as a feedback in a .dbc or .ipynb response notebook.

- The AutoGrader creates a bunch of local files that can be used for hunting down errors.

- The folder `SolutionWTest` has the student solutions with the corresponding TEST cells inserted.

- The folder `StudentSubmission` has the student solutions that are downloaded from Studium.

- The folder `Response` contains the student solutions with TEST cells already executed, but the TEST cell contents are removed and left only with the outputs. These notebooks are uploaded to Studium as responses for students.

> NOTE ! 
> The grading process starts at `start_date`. After completing grading student submissions for one round, it sleeps for 30 minutes and starts another round of grading again and again (in case students resubmit assignments or have just submitted them for the first time) until the `end_date`. If the assignment period has not started yet, the NotebookGrader will check once every 24 hours.

### Final Notes !
1. For databricks, if the notebook default language is Scala, all the code cells without a magic line (%scala or %python) will be treated as Scala. This also applies to Python.
2. The `configGrader.json` contains grading windows, and if you do not supply the master files before the grading window, the AutoGrader may crash. Then, one has to restart the `Grader.py`
