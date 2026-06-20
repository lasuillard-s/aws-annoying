
# ❤️‍🔥 Contributing to this project

Thank you for your interest in contributing to **aws-annoying**!

## 🐛 Reporting issues

Please report issues in our [GitHub repository](https://github.com/lasuillard-s/aws-annoying/issues). Before filing a new issue, search existing issues to avoid duplicates.

## 🏗️ Project overview

This project provides utilities and examples to help with common, annoying AWS tasks.

- CLI application (`aws-annoying`): Command-line interface for common AWS tasks
- Python library (`aws_annoying`): Utility functions for AWS operations
- Browser user scripts: Enhance the AWS Console experience
- Dev Container Features: Dev Container Features for setting up development environments

### 🛠️ Tech stack

This project uses the following technologies:

- [Python](https://www.python.org) 3.10+
- [uv](https://docs.astral.sh/uv/) for dependency management and packaging
- [Typer](https://typer.tiangolo.com) for command-line interface
- [Ruff](https://docs.astral.sh/ruff/) for linting and formatting, and [Mypy](https://mypy-lang.org) for type checking
- [pytest](https://docs.pytest.org/en/latest) and [nox](https://nox.thea.codes/en/stable/) for testing
- [MkDocs](https://www.mkdocs.org) for documentation

### 📂 Key directory structure

- `aws_annoying/`: The project's source code
- `console/`: User scripts for the AWS Console
- `devcontainer-features/`: Dev Container Features for development environment setup
- `docs/`: Project documentation
- `examples/`: Project usage examples
- `tests/`: Project tests
- `docker-compose.yaml`: Service containers for local development
- `flake.nix`: Flake configuration for the development environment
- `Justfile`: Commands for development
- `mkdocs.yaml`: MkDocs configuration
- `pyproject.toml`: Project dependencies and configuration

## 🔧 Set up the development environment

For development, the following tools are required.

### ❄️ Tools managed via Nix Flakes

This repository uses [Nix Flakes](https://nix.dev/concepts/flakes.html) to manage tools. The following tools are installed automatically (requires `nix`):

- `pre-commit`
- `just`
- `uv`
- `pipx`
- AWS CLI (`aws`)

Run `nix develop` to start the development environment, then run `just install` to install dependencies.

If you prefer using a [Dev Container](https://containers.dev), a configuration file ([devcontainer.json](./.devcontainer.example/devcontainer.json)) is provided with Nix preinstalled.

## ✅ Verifying changes

Before pushing your code, verify that your changes adhere to the project's coding standards. Run `just ci` to execute linters, formatters, and tests. Alternatively, let the `pre-commit` hooks handle this automatically.

## ✨ Submitting changes

Please submit pull requests on GitHub. Before opening a pull request, ensure your changes pass all checks by running `just ci`.

## 🚀 Release process

This project's artifacts are published to multiple channels:

- `aws-annoying` CLI and library: published to [PyPI](https://pypi.org/project/aws-annoying/), following this process:
  1. Prepare a release via the `Prepare Release` workflow: [workflow link](https://github.com/lasuillard-s/aws-annoying/actions/workflows/main_prepare-release.yaml).
  1. Review and merge the preparation pull request.
  1. Create and publish a new release in GitHub Releases.
  1. The `main_release.yaml` workflow ([.github/workflows/main_release.yaml](.github/workflows/main_release.yaml)) will publish the package to PyPI when a release is published.
- User scripts: hosted in the repository under `console/` and installable via user script engines; changes are applied by pushing to the `main` branch.
- Dev Container Features: published to GitHub Packages via the `devcf_release.yaml` workflow when changes are pushed to the `main` branch.
- Documentation: published to GitHub Pages via the `docs.yaml` workflow when changes are pushed to the `main` branch or to a `v*` tag.
