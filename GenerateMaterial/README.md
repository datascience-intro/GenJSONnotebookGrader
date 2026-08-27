# Generated material

This directory may hold private generated assignment artifacts for a local
grader installation. Production release automation should generate student
and private variants into fresh staging directories by passing explicit paths
to `generateIDSNotebooks.py` and
`generateIDSAssignmentMasterNotebooks.py`.

No `Master` or course-output symlink is required. Do not point generation at a
public repository. Install a validated `Assignment_N_problem_TEST.ipynb` here
only together with the matching `grader-manifest.json` entry and hashes.
