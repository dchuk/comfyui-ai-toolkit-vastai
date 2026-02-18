#!/bin/bash

utils=/opt/supervisor-scripts/utils
. "${utils}/logging.sh"
. "${utils}/cleanup_generic.sh"
. "${utils}/environment.sh"
. "${utils}/exit_portal.sh" "AI Toolkit"

# Activate environments
. /venv/main/bin/activate
. /opt/nvm/nvm.sh

# Not first boot — reinstall requirements to handle dependency drift after updates
if [[ ! -f /.provisioning ]]; then
    cd "${WORKSPACE}/ai-toolkit"
    uv pip --no-cache-dir install timm==1.0.22
    uv pip --no-cache-dir install -r requirements.txt
fi

# Wait for provisioning to complete
while [ -f "/.provisioning" ]; do
    echo "$PROC_NAME startup paused until instance provisioning has completed (/.provisioning present)"
    sleep 5
done

echo "Starting AI Toolkit"
cd "${WORKSPACE}/ai-toolkit/ui"
${AI_TOOLKIT_START_CMD:-npm run start} 2>&1
