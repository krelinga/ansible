#! /usr/bin/bash
FAILED=0
for file in "$@"; do
    # If the file doesn't start with the vault header, it might be unencrypted
    if ! grep -q '^$ANSIBLE_VAULT;' "$file"; then
        echo "ERROR: $file does not look encrypted with Ansible Vault!"
        FAILED=1
    fi
done
exit $FAILED