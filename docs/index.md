# aws-annoying

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![codecov](https://codecov.io/gh/lasuillard-s/aws-annoying/graph/badge.svg?token=gbcHMVVz2k)](https://codecov.io/gh/lasuillard-s/aws-annoying)
[![PyPI - Version](https://img.shields.io/pypi/v/aws-annoying)](https://pypi.org/project/aws-annoying/)

Utilities to handle annoying AWS tasks.

## ✨ Features

- **CLI application**: Command-line interface for handling common, annoying AWS tasks
- **Python library**: Reusable utility functions for AWS operations
- **Console enhancements**: Browser user scripts to improve the AWS Console experience
- **Dev Container Features**: Reusable Dev Container Features for development environments

## 🚀 Quick start

It is recommended to use [pipx](https://pipx.pypa.io/stable/) to install `aws-annoying` CLI:

```bash
$ TYPER_USE_RICH=0 pipx run aws-annoying --help
Usage: aws-annoying [OPTIONS] COMMAND [ARGS]...

Options:
  --version                 Show the version and exit.
  --quiet / --no-quiet      Disable outputs.  [default: no-quiet]
  --verbose / --no-verbose  Enable verbose outputs.  [default: no-verbose]
  --dry-run / --no-dry-run  Enable dry-run mode. If enabled, certain commands
                            will avoid making changes.  [default: no-dry-run]
  --install-completion      Install completion for the current shell.
  --show-completion         Show completion for the current shell, to copy it
                            or customize the installation.
  --help                    Show this message and exit.

Commands:
  load-variables   Wrapper command to run command with variables from AWS...
  ecs              ECS (Elastic Container Service) utility commands.
  mfa              Commands to manage MFA authentication.
  session-manager  AWS Session Manager CLI utilities.
```

You can also install the package via `pip` if you want to use its utility functions:

```bash
$ pip install aws-annoying
```

Please refer to the [documentation](https://lasuillard-s.github.io/aws-annoying/) for more information on how to use the application and package.

### 🐒 Browser User Scripts

To use browser user scripts to improve your AWS Console experience, download the scripts from the [console]((https://github.com/lasuillard-s/aws-annoying/blob/main/console) directory and install them in your browser.

Note that these scripts are provided "as is" and may not work in all cases.

### 🐳 Dev Container Features

You can use the Dev Container Features provided in [devcontainer-features]((https://github.com/lasuillard-s/aws-annoying/blob/main/devcontainer-features/) directory to help set up development containers. For example, add it in your `devcontainer.json` file:

```json
{
  "features": {
    "ghcr.io/lasuillard-s/aws-annoying/session-manager-plugin:0": {}
  }
}
```

## 💖 Contributing

Please refer to [CONTRIBUTING.md]((https://github.com/lasuillard-s/aws-annoying/blob/main/CONTRIBUTING.md) for more information on how to contribute to this project.

## 📜 License

This project is licensed under the MIT License.
