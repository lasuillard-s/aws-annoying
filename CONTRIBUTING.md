# ❤️‍🔥 Contributing to this project

Thank you for your interest in contributing to **aws-annoying**!

## 🐛 Reporting issues

Please report issues in our [GitHub repository](https://github.com/lasuillard-s/aws-annoying/issues). Before submitting an issue, please search for existing issues to avoid duplicates.

## 🏗️ Project overview

This project provides a set of utilities and examples to help with annoying AWS tasks.

- CLI application (`aws-annoying`): Command-line interface for handling annoying AWS tasks
- Python library (`aws_annoying`): Utility functions for AWS operations
- Browser user scripts: Enhance the AWS Console experience
- Dev Container Features: Dev Container Features for setting up development environments

### 🛠️ Tech stack

This project uses the following tech stack:

- [Python](https://www.python.org) 3.10+
- [uv](https://docs.astral.sh/uv/) for dependency management and packaging
- [Ruff](https://docs.astral.sh/ruff/) to lint and format Python code, and [mypy](https://mypy-lang.org) for type checking
- [pytest](https://docs.pytest.org/en/latest) for testing

### 📂 Key directory structure

- `aws_annoying/`: The project's source code
- `console/`: User scripts for the AWS Console
- `devcontainer-features/`: Dev Container Features for development environment setup
- `docs/`: Project documentation
- `examples/`: Project usage examples
- `tests/`: Project tests
- `flake.nix`: Flake configuration for the development environment
- `Justfile`: Commands for development
- `pyproject.toml`: Project dependencies and configuration

## 🔧 Set up the development environment

For development, the following tools are required:

### ❄️ Tools managed via Nix Flakes

This repository uses [Nix Flakes](https://nix.dev/concepts/flakes.html) to manage tools. The following tools are automatically installed (requires `nix` to be installed):

- `pre-commit`
- `just`
- `uv`
- `pipx`
- AWS CLI (`aws`)

Simply run `nix develop` to start the development environment, then run `just install` to install dependencies.

If you prefer using a [Dev Container](https://containers.dev), a configuration file ([devcontainer.json](./.devcontainer.example/devcontainer.json)) is provided with Nix pre-installed.

## ✅ Verifying changes

Before pushing your code, verify that your changes adhere to the project's coding standards. Run `just ci` to execute all necessary linters, formatters, and tests. Alternatively, let the `pre-commit` hooks handle this automatically.

## ✨ Submitting changes

Please feel free to submit pull requests on GitHub. Before opening a PR, ensure your changes pass all checks by running `just ci`.

## 🚀 Release process

This project's artifacts are published to multiple channels:

- `aws-annoying` CLI and library: [PyPI](https://pypi.org/project/aws-annoying/), following below process
  1. Prepare release via [Prepare Release](https://github.com/lasuillard-s/aws-annoying/actions/workflows/main_prepare-release.yaml) workflow.
  1. Review and merge the preparation PR.
  1. Create and publish a new release in GitHub Releases.
  1. [main_release.yaml](./.github/workflows/main_release.yaml) workflow will publish to PyPI when new releases are published.
- User scripts: [GitHub](https://github.com/lasuillard-s/aws-annoying/tree/main/console), installable via user script engines. You don't need to do anything other than push changes to the `main` branch.
- Dev Container Features: [GitHub Packages](https://github.com/orgs/lasuillard-s/packages?repo_name=aws-annoying) via [devcf_release.yaml](./.github/workflows/devcf_release.yaml) workflow when changes are pushed to the `main` branch.
