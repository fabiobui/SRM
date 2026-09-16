"""PostToolUse hook: run pre-commit on the file Claude just wrote/edited.

Reads the tool-call JSON from stdin, extracts the touched file path, and runs
`pre-commit run --files <path>` on it (via the same Python interpreter that
ran this hook, so it picks up whatever environment `python`/`pre-commit` is
installed into). Failures are surfaced back to Claude via additionalContext
so they can be fixed inline, without blocking the turn.
"""

import json
import os
import subprocess
import sys


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return

    file_path = data.get("tool_input", {}).get("file_path") or data.get(
        "tool_response", {}
    ).get("filePath")
    if not file_path or not os.path.isfile(file_path):
        return

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pre_commit", "run", "--files", file_path],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=90,
        )
    except Exception:
        return

    if result.returncode == 0:
        return

    output = (result.stdout + result.stderr).strip()
    print(
        json.dumps(
            {
                "systemMessage": f"pre-commit flagged issues in {file_path}",
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": (
                        f"pre-commit run on {file_path} found issues "
                        "(some may already be auto-fixed in the "
                        f"file):\n{output}"
                    ),
                },
            }
        )
    )


if __name__ == "__main__":
    main()
