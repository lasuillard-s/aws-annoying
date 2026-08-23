# ruff: noqa: D103, T201
from __future__ import annotations

import os

import nox

nox.options.default_venv_backend = "uv"


# * Python and Django version is parametrized at the CI level for coverage tracking
@nox.session()
@nox.parametrize(
    # Parametrize tests with different combinations of extra dependencies
    "extras",
    [
        [],
        ["cli"],
    ],
)
def tests(
    session: nox.Session,
    *,
    extras: list[str],
) -> None:
    is_gha = bool(os.environ.get("GITHUB_ACTIONS"))
    try:
        if is_gha:
            print(f"::group::{session.name}")

        session.run_install("uv", "sync", "--quiet", *[f"--extra={extra}" for extra in extras])

        marks = ["-m", "not cli"] if "cli" not in extras else []
        session.run("uv", "run", "pytest", "--cov-append", *marks)
    finally:
        if is_gha:
            print("::endgroup::")
