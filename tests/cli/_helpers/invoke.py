from __future__ import annotations

import os
import subprocess


def invoke_cli(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        ["uv", "run", "aws-annoying", *args],  # noqa: S607
        check=False,
        capture_output=True,
        text=True,
        env=(env or os.environ),  # * `AWS_ENDPOINT_URL` should be inherited appropriately to use Moto or LocalStack
    )
