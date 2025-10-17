# aws-annoying

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![codecov](https://codecov.io/gh/lasuillard-s/aws-annoying/graph/badge.svg?token=gbcHMVVz2k)](https://codecov.io/gh/lasuillard-s/aws-annoying)
[![PyPI - Version](https://img.shields.io/pypi/v/aws-annoying)](https://pypi.org/project/aws-annoying/)

Utils to handle some annoying AWS tasks.

## ❓ About

This project aims to provide a set of utilities and examples to help with some annoying tasks when working with AWS.

Major directories of the project:

- **aws_annoying** Python package containing CLI and utility functions.
- **console** Utilities to help working with AWS Console.
- **examples** Examples of how to use the package.

## 🚀 Installation

It is recommended to use [pipx](https://pipx.pypa.io/stable/) to install `aws-annoying` CLI:

```bash
$ pipx install aws-annoying
$ aws-annoying --help

 Usage: aws-annoying [OPTIONS] COMMAND [ARGS]...

...
```

As the package also provides some utility functions, you can install `aws-annoying` via pip, if you are going to use those utils.

## 💡 Usage

Below are brief explanation of available commands. For more detailed information about commands, please refer to the CLI help.

### `ecs task-definition-lifecycle`

Expire and delete ECS task definitions based on criteria.

### `ecs wait-for-deployment`

Wait for ECS deployment to start, complete or fail, and stabilize.

### `load-variables`

Wrapper command to run command with variables from various AWS resources (SSM Parameter Store, Secrets Manager, etc.) injected as environment variables.

### `mfa configure`

Configure AWS profile or refresh session for MFA.

### `session-manager install`

Install AWS Session Manager plugin.

### `session-manager port-forward`

Start a port forwarding session using AWS Session Manager.

### `session-manager start`

Start new session via Session Manager.

### `session-manager stop`

Stop running port forwarding session for PID file.

## 💖 Contributing

Any feedback, suggestions or contributions are welcome! Feel free to open an issue or a pull request.
