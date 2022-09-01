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


def initConfigFiles(assName):
    with open("./configGrader.json", mode="r") as f:
        grader_conf = json.load(f)

    course_id = grader_conf['course']
    dbc_cluster_id = grader_conf['dbc_cluster_id']
    with open("./Grading/create-job-template.json", mode="r") as f:
        job_conf = json.load(f)
        job_conf["name"] = assName
        job_conf["existing_cluster_id"] = dbc_cluster_id
        job_conf["notebook_task"]["notebook_path"] = grader_conf["dbc_workspace_dir"] + "/Grading/" + assName + "/Graded_Notebook_for_" + assName + ".dbc"
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


