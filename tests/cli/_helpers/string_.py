from __future__ import annotations

import re


def normalize_console_output(output: str, *, replace: dict[str, str] | None = None) -> str:
    """Normalize the console output for easier comparison."""
    # Remove leading and trailing spaces
    output = output.strip()

    # Unwrap each line
    output = re.sub(r"[ ]+\n", " ", output)

    # Handle Windows path separator
    output = output.replace("\\", "/")

    # Extra replacements; e.g. temporary paths that may vary
    if replace:
        for old, new in replace.items():
            output = output.replace(old, new)

    return output
