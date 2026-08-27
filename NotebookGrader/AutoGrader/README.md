# AutoGrader operation

The supported Jupyter entry point is the repository-root `Grader.py`. Its
default mode cannot upload scores, comments, or response files. Canvas writes
require `--apply` (or its compatibility alias `--sharp`).

Keep `configGrader.json` local, ignored, untracked, and preferably mode 600.
Use the complete redacted `configGrader.json.template`; never commit a token.
Before Canvas is constructed, the entry point validates:

- Git ignore/tracking state and local configuration structure;
- course ID, exact assignment names, IDs, and timezone-aware grading windows;
- the cumulative release list in `grader-manifest.json`;
- installed `problem_TEST` and canonical source SHA-256 values;
- `problem_TEST` notebook structure;
- Epicbox, Docker image, course data, and `Utils.py`.

Run the local-only preflight and one controlled non-writing pass first:

```bash
python3.11 Grader.py --assignment 1 --preflight-only
python3.11 Grader.py --assignment 1 --once
```

Optionally select one known submission with `--submission-user USER_ID`. Only
after the public assignment and Canvas settings have been reviewed should a
live round be enabled:

```bash
python3.11 Grader.py --assignment 1 --once --apply
```

The Jupyter schedule uses `Europe/Stockholm`, keeps the 23:59 end-of-day
cutoff, and polls twice daily by default. See the root README for the manifest
contract and all command-line options.

The older Databricks classes remain available for legacy integrations, but
their platform-specific workspace setup is not the supported 1MS041 Jupyter
release path.
