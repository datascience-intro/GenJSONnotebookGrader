import requests
import json
import os
from databricks_cli.sdk.api_client import ApiClient
from databricks_cli.workspace.api import WorkspaceApi, WorkspaceFileInfo
from databricks_cli.workspace.cli import *
from databricks_cli.configure.provider import *
from databricks_cli.clusters.api import ClusterApi
from databricks_cli.jobs.api import JobsApi
from databricks_cli.jobs.cli import *
from databricks_cli.runs.api import RunsApi
import json
import time

from zipfile import ZipFile

with open("./configGrader.json", mode="r") as f:
        grader_conf = json.load(f)
with open("./configNotebooks.json", mode="r") as f:
    notebook_conf = json.load(f)
api_client = ApiClient(
                host  = get_config().host,
                token = get_config().token
                )
workspace = WorkspaceApi(api_client)

def upload_generated_assignments(grader_conf,assignment_name=None):
    api_client = ApiClient(
                host  = get_config().host,
                token = get_config().token
                )
        
    workspace = WorkspaceApi(api_client)
    assignment_name = "Test Final Assignment"
    
    workspace_assignment_path = grader_conf["dbc_workspace_dir"] + "/" + assignment_name + "/AutoGrader generated assignments"
    workspace.mkdirs(workspace_assignment_path)
    names = os.listdir("courseLink/GenerateMaterial/generated_assignments")
    #names = [name if os.listdir("./generated_assignments")
    local_assignment_name = grader_conf["Assignments"][0]["master_filename"]
    #oh lord
    assNumber = local_assignment_name.split(".")[0].split("/")[1].split("_")[1]
    #notebooks_to_upload = [name if "Assignment_" + assNumber in name for name in names]
    if names != []:
        for filename in names:
            if "Assignment_" + assNumber + "_" in filename:
            #if filename.split(".")[-1] == "dbc":
                
                upload_notebook(filename,assignment_name,workspace,workspace_assignment_path)
            #break

def upload_notebook(filename,assName,workspace,workspace_path):    
    try:
        workspace.delete(workspace_path+ "/" + filename.split(".")[0],is_recursive=False)
    except:
        #already exists
        pass
    workspace.import_workspace("courseLink/GenerateMaterial/generated_assignments/"+filename,workspace_path + "/" + filename.split(".")[0] ,"DBC","DBC",is_overwrite=False)

    print("upload notebook " + filename + " to workspace")

def download_master(grader_conf,notebook_conf):
    api_client = ApiClient(
                host  = get_config().host,
                token = get_config().token
                )

    
    #with open("../configGrader.json", mode="r") as f:
    #    grader_conf = json.load(f)
    #with open("../configNotebooks.json", mode="r") as f:
    #    notebook_conf = json.load(f)
    
    assName = grader_conf["Assignments"][0]["name"]
    
    
    workspace = WorkspaceApi(api_client)
    #master_filename = notebook_conf["master_notebooks"][0].split(".")[0] #temporary solution
    workspace_master_path = grader_conf["dbc_workspace_dir"] + "/" + assName + "/" + notebook_conf["master_notebooks"][0]
    print(os.getcwd())
    workspace.export_workspace(workspace_master_path,notebook_conf["notebook_folder"] + "/" + notebook_conf["master_notebooks"][0] + ".dbc","DBC","DBC")
    print("downloaded notebook" + workspace_master_path + "from workspace")
    
    
def upload_feedback_to_workspace(file,user_name,user_id,attemptnr):

    #workspace.import_workspace(file,grader_conf["dbc_workspace_dir"] + "/" + grader_conf["Assignments"][0]["name"] + "/Grading_Archive/" + grader_conf["Assignments"][0]["name"] + "_" + + user_name + "_" + user_id + attemptnr,"DBC","DBC",is_overwrite=False)
    pass

    
def initConfigFiles(assName):
    with open("./configGrader.json", mode="r") as f:
        grader_conf = json.load(f)

    course_id = grader_conf['course']
    dbc_cluster_id = grader_conf['dbc_cluster_id']
    with open("./Grading/create-job-template.json", mode="r") as f:
        job_conf = json.load(f)
        job_conf["name"] = assName
        job_conf["existing_cluster_id"] = dbc_cluster_id
        job_conf["notebook_task"]["notebook_path"] = grader_conf["dbc_workspace_dir"] + "/" + grader_conf["Assignments"][0]["name"] + "/Grading/Graded_Notebook_for_" + assName + ".dbc"
    return job_conf,grader_conf

def startCluster(api_client, cluster_id):
    cluster = ClusterApi(api_client)
    if cluster.get_cluster(cluster_id)['state'] != 'RUNNING':
        if cluster.get_cluster(cluster_id)['state'] != 'STARTING' and cluster.get_cluster(cluster_id)['state'] != 'PENDING':
            cluster.start_cluster(cluster_id)
            print("Starting cluster ",cluster.get_cluster(cluster_id)['cluster_name'])
        while cluster.get_cluster(cluster_id)['state'] != 'RUNNING':
            print("Cluster is not running yet")
            time.sleep(30)
            continue
        print("Cluster started")
    print("===== Cluster is running =====")

def createAndRunJob(api_client, job_conf):
    jobs_api = JobsApi(api_client)
    job_id = jobs_api.create_job(job_conf)
    print("Job created with id: ", job_id)
    run = jobs_api.run_now(job_id['job_id'],None,None,None,None)
    runs_api = RunsApi(api_client)
    #keep track of ru
    result_state = runs_api.get_run(run['run_id'])['state']['life_cycle_state']

    while result_state in ['PENDING','RUNNING']:
        print("job state: ",result_state)
        print("Job run is not finished yet")
        time.sleep(15)
        result_state = runs_api.get_run(run['run_id'])['state']['life_cycle_state']

    print("Run finished")
    print("-----\n----- start downloading job result")
    return run['run_id']




## using these funcitons given from databricks ##
## code: https://docs.databricks.com/_static/examples/extract.py
## Runs export: https://docs.databricks.com/dev-tools/api/2.0/jobs.html#jobsjobsserviceexportrun

def output_location(dir_name, file_name, ext="html"):
    return "%s/%s.%s" % (dir_name, file_name.split(".")[0], ext)


def extract_content(input_file, output_dir):
    with open(input_file, 'r') as reader:
        exported_content = reader.read()
    data = json.loads(exported_content).get("views")
    output_file_names = set()
    for element in data:
        if element.get("type", None).lower() != "notebook":
            continue
        output_file = element.get("name")
        counter = 0
        while output_file in output_file_names:
            counter += 1
            output_file = "%s_%d" % (output_file, counter)
        output_file_names.add(output_file)
        with open(output_location(output_dir, output_file), "w") as writer:
            writer.write(str(element.get("content", "")))
    print(", ".join([output_location(output_dir, f) for f in output_file_names]))


