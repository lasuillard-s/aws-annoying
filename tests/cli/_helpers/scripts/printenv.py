#!/usr/bin/env python
"""Test helper script to print environment variables.

This script is slightly different from `printenv` command in Unix-like systems.

- It prints the environment variables' with the provided keys only.
- If variable is not found, it prints an empty string to easily compare with the expected value.
"""

import argparse
import json
import os
import sys


def main() -> None:
    """Print the environment variables."""
    parser = argparse.ArgumentParser(description="Print the environment variables.")
    parser.add_argument("--json", action="store_true", help="Print the environment variables as JSON.", default=False)
    parser.add_argument("keys", nargs="*", help="The keys to print.")
    ns = parser.parse_args()

    # Arguments
    keys: list[str] = ns.keys
    as_json: bool = ns.json

    # Print the environment variables
    env = {key: os.environ.get(key, "") for key in keys}
    if as_json:
        sys.stdout.write(f"{json.dumps(env)}\n")
    else:
        sys.stdout.writelines(f"{k}={v}\n" for k, v in env.items())


if __name__ == "__main__":
    main()
