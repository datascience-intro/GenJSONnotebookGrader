# GenJSONnotebookGrader

GenJSONnotebookGrader parses canonical course master notebooks, produces
student and private assignment variants, and can grade Jupyter submissions in
Studium through Canvas. Jupyter generation is independent of the live grader:
it neither imports Canvas nor changes network/TLS settings.

## Supported generation environment

The supported generation runtime is Python 3.11 and `nbformat==5.10.4`. The
version and dependency are declared in `pyproject.toml`.

```bash
python3.11 -m pip install .
```

Docker, Epicbox, the Canvas connector, and course execution dependencies are
needed only for live grading, not for notebook generation or `--check`.

## Notebook configuration

Copy `configNotebooks.json.template` to a course-owned JSON file and edit it.
The generator does not require that file to live in this repository. Relative
paths in the JSON are resolved from the JSON file's directory. Command-line
path overrides are resolved from the invocation directory; release wrappers
should pass absolute paths.

The `assignments` list is a release gate. The only valid values are `[]`,
`[1]`, `[1, 2]`, `[1, 2, 3]`, and `[1, 2, 3, 4]`. An unreleased assignment
master produces a one-cell student placeholder. A released assignment also
produces its student problem notebook and, through the private command, these
four variants:

- `Assignment_N_problem.ipynb`
- `Assignment_N_problem_TEST.ipynb`
- `Assignment_N_solution_TEST.ipynb`
- `Assignment_N_problem_solution.ipynb`

Master names must be unique and all master files must exist. The source,
student output, and private output directories must be distinct.

## Generate and validate

Both entry points accept the same explicit path options and work from any
directory. No course or output symlink is required.

```bash
python3.11 generateIDSNotebooks.py \
  --config /path/to/configNotebooks.course.json \
  --source-dir /path/to/course/master/jp \
  --output-dir /tmp/student-stage \
  --assignment-output-dir /tmp/grader-stage

python3.11 generateIDSAssignmentMasterNotebooks.py \
  --config /path/to/configNotebooks.course.json \
  --source-dir /path/to/course/master/jp \
  --output-dir /tmp/student-stage \
  --assignment-output-dir /tmp/grader-stage
```

The private generator can also build an assignment without adding it to the
configuration's release list. This keeps unreleased work out of student output:

```bash
python3.11 generateIDSAssignmentMasterNotebooks.py \
  --config /path/to/configNotebooks.course.json \
  --assignment 2
```

Repeat `--assignment` to generate more than one explicitly selected assignment.
Each selected assignment must have an `Assignment_N.ipynb` entry in
`master_notebooks`.

The same operation is available in `CLI.py` under **Generate Material and
Assignments → Generate Assignment by Number**.

Use `--list` to show resolved inputs and outputs without parsing or writing.
Use `--check` to parse and validate the generated artifacts in memory without
creating either output directory. Add `--verbose` for per-file output.
Generation validates every notebook before it starts writing. Publication
automation should still use fresh staging directories and validate the staged
artifacts before synchronizing them elsewhere.

## Safe Studium grader

`configGrader.json` is a local secret file. It must remain ignored and
untracked; `Grader.py` verifies both conditions before reading Canvas. Start
from `configGrader.json.template`, replace its redacted values locally, and
prefer owner-only permissions:

```bash
cp configGrader.json.template configGrader.json
chmod 600 configGrader.json
```

An installed `grader-manifest.json` is optional. Without one, the grader uses
the assignments and master filenames in `configGrader.json` and still validates
the structure of each master notebook. To enable stricter release and integrity
checks, set `grader_manifest` in the configuration or pass `--manifest`; the
manifest records the installed `problem_TEST` filename, its SHA-256, and the
SHA-256 of the current canonical `Assignment_N.ipynb`.

Local preflight also checks the configured Docker image, Epicbox, course data,
and `Utils.py`. It does not contact Canvas:

```bash
python3.11 Grader.py --assignment 1 --preflight-only
```

The default mode is non-writing. During an active grading window it downloads
and grades at most one controlled submission, but does not upload a score,
comment, or file:

```bash
python3.11 Grader.py --assignment 1 --once
python3.11 Grader.py --assignment 1 --submission-user 123456 --once
```

Canvas writes require the explicit `--apply` (or `--sharp`) flag. Review the
public notebook and Canvas assignment manually before using it:

```bash
python3.11 Grader.py --assignment 1 --once --apply
```

Grading windows use timezone-aware `Europe/Stockholm` datetimes and end at
23:59 on the configured end date. The default polling interval is 43,200
seconds (twice daily); `--poll-seconds` overrides it for one run.

## Tests

```bash
python3.11 -m unittest discover -s tests -v
```
