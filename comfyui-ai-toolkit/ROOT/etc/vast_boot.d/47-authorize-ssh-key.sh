#!/bin/bash
# IMPORTANT: This script is SOURCED by boot_default.sh (not executed).
# Do NOT use `set -euo pipefail` (it propagates to the parent shell and breaks
# subsequent boot scripts). Do NOT use `exit` (use `return`).
#
# Authorizes an SSH public key supplied via the SSH_PUBLIC_KEY env var. This is
# needed because we launch in entrypoint/args mode, where VastAI runs the image
# as-is and does NOT inject account SSH keys. The `vast` CLI passes the user's
# public key automatically; setting it manually in the template env also works.

. /etc/environment 2>/dev/null || true

if [[ -n "${SSH_PUBLIC_KEY:-}" ]]; then
    mkdir -p /root/.ssh && chmod 700 /root/.ssh
    touch /root/.ssh/authorized_keys && chmod 600 /root/.ssh/authorized_keys
    if ! grep -qF "${SSH_PUBLIC_KEY}" /root/.ssh/authorized_keys 2>/dev/null; then
        echo "${SSH_PUBLIC_KEY}" >> /root/.ssh/authorized_keys
        echo "[authorize-ssh-key] added SSH_PUBLIC_KEY to root authorized_keys"
    else
        echo "[authorize-ssh-key] SSH_PUBLIC_KEY already present"
    fi
else
    echo "[authorize-ssh-key] no SSH_PUBLIC_KEY set; skipping"
fi
