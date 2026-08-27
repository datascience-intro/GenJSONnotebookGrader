# Jupyter quick start

1. Install the pinned generation package with Python 3.11.

   ```bash
   python3.11 -m pip install .
   ```

2. Copy `configNotebooks.json.template` into the course repository. Set the
   canonical master list, course metadata, output defaults, and cumulative
   `assignments` release list. Relative JSON paths are relative to that file;
   no `courseLink`, `Master`, or output symlink is needed.

3. Preview and validate without writing.

   ```bash
   python3.11 /path/to/GenJSONnotebookGrader/generateIDSNotebooks.py \
     --config /path/to/course/GenerateMaterial/configNotebooks.course.json \
     --source-dir /path/to/course/master/jp \
     --output-dir /tmp/student-stage \
     --assignment-output-dir /tmp/grader-stage \
     --list

   python3.11 /path/to/GenJSONnotebookGrader/generateIDSNotebooks.py \
     --config /path/to/course/GenerateMaterial/configNotebooks.course.json \
     --source-dir /path/to/course/master/jp \
     --output-dir /tmp/student-stage \
     --assignment-output-dir /tmp/grader-stage \
     --check
   ```

4. Generate student and private artifacts into fresh staging directories by
   running `generateIDSNotebooks.py` and
   `generateIDSAssignmentMasterNotebooks.py` with the same four path options.
   Validate and review those exact staged files before publication or grader
   installation.

5. For grading, create ignored `configGrader.json` from its redacted template
   and install the validated `problem_TEST` file together with a matching
   `grader-manifest.json`. Run `Grader.py --assignment N --preflight-only`,
   then a non-writing `--once` pass. Use `--apply` only after manual review.
