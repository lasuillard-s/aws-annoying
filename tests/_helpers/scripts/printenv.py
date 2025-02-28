#!/usr/bin/env python
"""Test helper script to print environment variables.

This script is slightly different from `printenv` command in Unix-like systems.

- It prints the environment variables' with the provided keys only.
- If variable is not found, it prints an empty string to easily compare with the expected value.
"""

import argparse
import os
import sys


def main() -> None:
    """Print the environment variables."""
    parser = argparse.ArgumentParser(description="Print the environment variables.")
    parser.add_argument("keys", nargs="*", help="The keys to print.")
    ns = parser.parse_args()

    keys: list[str] = ns.keys

    for key in keys:
        value = os.environ.get(key, "")
        sys.stdout.write(f"{key}={value}\n")


if __name__ == "__main__":
    main()
