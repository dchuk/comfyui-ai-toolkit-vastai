#!/bin/bash

utils=/opt/supervisor-scripts/utils
. "${utils}/logging.sh"
. "${utils}/environment.sh"

# Entrypoint/args launch mode does NOT get VastAI's injected sshd, so we run our
# own. The public key is placed in /root/.ssh/authorized_keys by the boot hook
# 47-authorize-ssh-key.sh (from the SSH_PUBLIC_KEY env var). Starts early (no
# provisioning wait) so the instance is reachable for debugging while it boots.

mkdir -p /run/sshd
ssh-keygen -A   # generate any missing host keys

echo "[sshd] starting on port 22 (key-based root login)"

# Force the auth settings regardless of the base sshd_config: allow key-based
# root login, no passwords. StrictModes off as a perms failsafe.
exec /usr/sbin/sshd -D -e \
    -o PermitRootLogin=prohibit-password \
    -o PubkeyAuthentication=yes \
    -o PasswordAuthentication=no \
    -o StrictModes=no
