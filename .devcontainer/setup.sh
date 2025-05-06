#! /usr/bin/bash

set -e

echo "Installing ansible-galaxy dependencies..."
ansible-galaxy install -r requirements.yaml
echo
echo "injecting python requirements into ansible-core..."
pipx inject ansible-core -r requirements.txt