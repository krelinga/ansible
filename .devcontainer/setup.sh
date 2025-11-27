#! /usr/bin/bash

set -e

echo "Installing postgresql..."
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib libpq-dev
sudo apt-get clean && sudo rm -rf /var/lib/apt/lists/*
echo
echo "Installing ansible-galaxy roles..."
ansible-galaxy role install -r requirements.yaml -p ./.ansible/roles --force
echo
echo "Installing ansible-galaxy collections..."
ansible-galaxy collection install -r requirements.yaml -p ./.ansible/collections --force
echo
echo "injecting python requirements into ansible-core..."
pipx inject ansible-core -r requirements.txt
echo
echo "installing pre-commit hooks..."
pre-commit install
