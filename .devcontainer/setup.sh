#! /usr/bin/bash

set -e

echo "Installing ansible-galaxy dependencies..."
ansible-galaxy install -r requirements.yaml
echo
echo "Installing bitwarden python sdk..."
pipx inject ansible-core bitwarden-sdk proxmoxer requests