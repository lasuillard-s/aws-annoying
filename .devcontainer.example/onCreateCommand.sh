#!/usr/bin/env bash

pipx install uv
pipx install pre-commit

# Ensure the user's home directory is owned by the user
sudo chown --recursive "$(id --user):$(id --group)" ~
sudo chmod --recursive 600 ~/.config/op ~/.aws
sudo chmod --recursive u=rwX,g=,o= ~/.config/op ~/.aws
