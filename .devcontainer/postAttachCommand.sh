#!/usr/bin/env bash

# Shortcuts for development
echo 'alias aa="uv run aws-annoying"' >> ~/.bashrc

sudo chown --recursive "$(id --user):$(id --group)" ~
sudo chmod --recursive 600 ~/.config/op ~/.aws
sudo chmod --recursive u=rwX,g=,o= ~/.config/op ~/.aws

make install
