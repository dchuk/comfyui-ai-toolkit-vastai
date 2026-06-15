#!/bin/bash

utils=/opt/supervisor-scripts/utils
. "${utils}/logging.sh"
. "${utils}/cleanup_generic.sh"
. "${utils}/environment.sh"

# Serverless
if [[ "${SERVERLESS:-false}" != "true" ]]; then
    . "${utils}/exit_portal.sh" "ComfyUI"
fi

COMFYUI_DIR=${WORKSPACE}/ComfyUI

# Activate the venv
. /venv/main/bin/activate

# Not first boot - Do this to handle frontend being out of sync after manager update
if [[ ! -f /.provisioning ]]; then
    cd "${COMFYUI_DIR}" || exit
    uv pip --no-cache-dir install -r requirements.txt
fi

# Wait for provisioning to complete
while [ -f "/.provisioning" ]; do
    echo "$PROC_NAME startup paused until instance provisioning has completed (/.provisioning present)"
    sleep 5
done

COMFYUI_ARGS=${COMFYUI_ARGS:---disable-auto-launch --port 18188 --enable-cors-header --enable-manager}

# Load the shared-model-paths config (shared /workspace/models tree + AI-Toolkit
# LoRA outputs) unless the user already supplied their own --extra-model-paths-config.
EXTRA_MODEL_PATHS=/opt/comfyui-config/extra_model_paths.yaml
if [[ -f "${EXTRA_MODEL_PATHS}" && "${COMFYUI_ARGS}" != *"--extra-model-paths-config"* ]]; then
    COMFYUI_ARGS="${COMFYUI_ARGS} --extra-model-paths-config ${EXTRA_MODEL_PATHS}"
fi

# Launch ComfyUI
cd "${COMFYUI_DIR}" || exit
# Intentional word-splitting: COMFYUI_ARGS must expand to multiple CLI args
# shellcheck disable=SC2086
LD_PRELOAD=libtcmalloc_minimal.so.4 \
        python main.py \
        ${COMFYUI_ARGS} 2>&1
