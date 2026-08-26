from __future__ import annotations

import re
import sys
from pathlib import Path

_BASE_DIR = Path(__file__).parent.parent.parent.parent


def normalize_console_output(output: str, *, replace: dict[str, str] | None = None) -> str:
    """Normalize the console output for easier comparison."""
    # Remove leading and trailing spaces
    output = output.strip()

    # Unwrap each line
    output = re.sub(r"[ ]+\n", " ", output)

    # Extra replacements; e.g. temporary paths that may vary
    replace = replace or {}
    replace.setdefault(sys.executable, "<PYTHON_EXECUTABLE>")
    replace.setdefault(str(_BASE_DIR), "<BASE_DIR>")
    for old, new in replace.items():
        output = output.replace(old, new)

    # Handle Windows path separator
    output = output.replace("\\", "/")

    # Strip ANSI escape sequences (e.g. color codes)
    output = re.sub(r"\x1b\[[0-9;]*m", "", output)

    return output  # noqa: RET504
