# GenJSONnotebookGrader

Oskar Åsbrink, Kristoffer Torp

2022, Uppsala, Sweden

This project was supported by Combient Mix AB through summer internships at:

Combient Competence Centre for Data Engineering Sciences,
Department of Mathematics,
Uppsala University, Uppsala, Sweden


This project is a refactoring and repackaging of work contributed by:
- Suparerk Angkawattanawit
- Benny Avelin
- Raazesh Sainudiin
- Tilo Wiklund

Don't hesitate to raise an issue if you encounter errors.

## Introduction to the NotebookGrader

This Notebook AutoGrader converts platform-specific notebooks to JSON to be able to run automatic grading of assignments that are then uploaded to Studium using the Canvas API. There is yet no support for grading For Jupyter notebooks through the CLI. See README.md for instructions on how to run manually.

## Overview

To use the NotebookGrader there are a couple of steps to follow:
0. Clone the NotebookGrader, test_course and CanvasInterface repositories. Put them beside each other in the same folder.
1. Create a 'Master' notebook. This is a notebook which contains cells of different types: lecture cells(optional),  problem cells, test cells and solution cells.
2. From the master notebook, you generate the following notebooks
    - Lecture notebook containing instruction cells, lecture cells etc
    - Problem_TEST notebook that the NotebookGrader uses to correct the student submission
    - Problem notebook for students to fill in
    - Solution notebook that can be submitted to Canvas as a "perfect" student to validate that the generation and grading works as expected
3. Run the NotebookGrader which will fetch student submissions from Canvas, grade them and upload the results to the student Canvas page.

## 0. Install necessary dependencies

The NotebookGrader will use the following dependencies:

`pip3 install python_on_whales`
`pip3 install databricks-cli`
`pip3 install simple_terminal_menu`
`pip3 install nbformat`

## 1. Create a Master notebook

The NotebookGrader needs the Master notebook to be in a specific format.
For instructions on how to create a master notebook see the readme in [Test_course](https://github.com/datascience-intro/test_course)

## 2. Set up config files, folders and symlinks

- Fill in configGrader.json and configNotebooks.json using the template file. In the Readme in NotebookGrader/AutoGrader you can find how to set up the config files more in detail. Set the symlink `courseLink` to the top level of your course repo or folder. Create a folder `GenerateMaterial` and inside it create `generated_assignments` inside. This is where generated notebooks will go.

- In your specified databricks workspace folder, create a folder with the same name as the assignment in studium. This is where you will put your master notebook.

## 3. Generate Assignment notebooks

- Check if you have the folder with the Canvas assignment name in your specified databricks workspace path. Check that the Master notebook is inside it with the name specified in configNotebooks["master_notebook"]. 
- Start the DBCLI
`python3 DBCLI.py`
and navigate to generate, Assignment notebook, assignment name, and generate all. After generation you can choose upload to databricks. These go to your Databricks workspace directory under assignment name and generated assignments.

## 4. Run the NotebookGrader
- start the DBCLI and choose grade. This will fetch submitted assignments every 30 minutes and grade them before uploading to the student Canvas page.
