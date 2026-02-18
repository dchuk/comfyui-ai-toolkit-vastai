#!/bin/bash
set -euo pipefail

# Source environment and utilities
. /etc/environment 2>/dev/null || true
. /opt/supervisor-scripts/utils/update.sh

# Check master switch — exit early if updates disabled
if [[ "${AUTO_UPDATE:-true}" != "true" ]]; then
    echo "Auto-update disabled (AUTO_UPDATE=${AUTO_UPDATE}), skipping"
    exit 0
fi

# Activate shared venv
. /venv/main/bin/activate

# Record PyTorch version before any package installs
torch_pre=$(python -c 'import torch; print(torch.__version__)') || {
    echo "WARNING: Could not determine PyTorch version, skipping validation"
    torch_pre=""
}

# ============================================================
# ComfyUI Update
# ============================================================
COMFYUI_DIR="${WORKSPACE:-/workspace}/ComfyUI"
comfyui_status="skipped"

if [[ -d "$COMFYUI_DIR" ]]; then
    comfyui_old=$(git -C "$COMFYUI_DIR" describe --tags --always 2>/dev/null || echo "unknown")

    # Determine target ref
    if [[ -n "${COMFYUI_VERSION:-}" ]]; then
        comfyui_target="$COMFYUI_VERSION"
    else
        comfyui_target=$(fetch_latest_github_release_tag Comfy-Org ComfyUI) || {
            echo "WARNING: Failed to fetch latest ComfyUI release, skipping update"
            comfyui_target=""
        }
    fi

    if [[ -n "$comfyui_target" ]]; then
        if safe_git_update "$COMFYUI_DIR" "$comfyui_target"; then
            cd "$COMFYUI_DIR"
            if uv pip --no-cache-dir install -r requirements.txt 2>&1; then
                # Validate PyTorch after pip install
                if [[ -n "$torch_pre" ]]; then
                    validate_pytorch_version "$torch_pre" || echo "CRITICAL: PyTorch version changed after ComfyUI requirements install"
                fi
                comfyui_status="updated"
            else
                echo "WARNING: ComfyUI pip install failed"
                comfyui_status="pip-failed"
            fi
        else
            echo "WARNING: ComfyUI git update failed, continuing with current version"
            comfyui_status="git-failed"
        fi
    fi
else
    echo "WARNING: ComfyUI directory not found at ${COMFYUI_DIR}"
    comfyui_status="not-found"
fi

exit 0
