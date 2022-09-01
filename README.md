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

This Notebook AutoGrader converts platform-specific notebooks to JSON to be able to run automatic grading through the Canvas API. 


This NotebookGrader supports:

1. Jupyter notebooks(*.ipynb*) with python and SageMath kernels
2. Databricks notebooks(*.dbc*) with support for Python and Scala.


## Overview

To use the NotebookGrader there are a couple of steps to follow:
0. Clone the NotebookGrader,test_course and CanvasInterface repositories. Put them beside each other in the same folder.
1. Create a 'Master' notebook. This is a notebooks which contains cells of different types: lecture cells(optional),  problem cells, test cells and solution cells. 
2. From the master notebook, you generate the following notebooks
    - Lecture notebook containing instruction cells, lecture cells etc
    - Problem_TEST notebook that the NotebookGrader uses to correct the student submission
    - Problem notebook for students to fill in
3. Run the NotebookGrader which will fetch student submissions from Canvas, grade them and upload the results.


## 1. Create a Master notebook
The NotebookGrader needs the Master notebook to be in a specific format.
For instructions on how to create a master notenook see the readme in [Test_course](https://github.com/datascience-intro/test_course)

## 2. Generate notebooks
For instructions on how to generate notebooks, see the readme in [Test_course](https://github.com/datascience-intro/test_course).

## 3. Run the NotebookGrader
For instructions on how to run the NotebookGrader, see the readme in NotebookGrader -> AutoGrader





