#!/bin/bash
# IMPORTANT: This script is SOURCED by boot_default.sh (not executed).
# Do NOT use `set -euo pipefail` (it propagates to the parent shell and breaks
# subsequent boot scripts). Do NOT use `exit` (it kills the parent shell and
# prevents 95-supervisor-wait.sh from removing /.provisioning).
# Use `return` instead of `exit`, and explicit error handling instead of set -e.

# Structured log function with auto-update prefix
log() { echo "[auto-update $(date +%H:%M:%S)] $*"; }

# Source environment and utilities
. /etc/environment 2>/dev/null || true
. /opt/supervisor-scripts/utils/update.sh

# Check master switch — return early if updates disabled
if [[ "${AUTO_UPDATE:-true}" != "true" ]]; then
    log "Auto-update disabled (AUTO_UPDATE=${AUTO_UPDATE}), skipping"
    return 0 2>/dev/null || true
fi

log "Starting auto-update check..."

# Activate shared venv
. /venv/main/bin/activate

# Record PyTorch version before any package installs
torch_pre=$(python -c 'import torch; print(torch.__version__)' 2>/dev/null) || {
    log "WARNING: Could not determine PyTorch version, skipping validation"
    torch_pre=""
}
[[ -n "$torch_pre" ]] && log "PyTorch version: ${torch_pre}"

# ============================================================
# ComfyUI Update (Comfy-Org/ComfyUI)
# ============================================================
COMFYUI_DIR="${WORKSPACE:-/workspace}/ComfyUI"
comfyui_status="skipped"
comfyui_old="unknown"
comfyui_new="unknown"

if [[ -d "$COMFYUI_DIR" ]]; then
    comfyui_old=$(git -C "$COMFYUI_DIR" describe --tags --always 2>/dev/null || echo "unknown")
    log "Updating ComfyUI (current: ${comfyui_old})..."

    # Determine target ref
    if [[ -n "${COMFYUI_VERSION:-}" ]]; then
        comfyui_target="$COMFYUI_VERSION"
        log "Using pinned ComfyUI version: ${comfyui_target}"
    else
        comfyui_target=$(fetch_latest_github_release_tag Comfy-Org ComfyUI 2>/dev/null) || {
            log "WARNING: Failed to fetch latest ComfyUI release, skipping update"
            comfyui_target=""
        }
        [[ -n "$comfyui_target" ]] && log "Latest ComfyUI release: ${comfyui_target}"
    fi

    if [[ -n "$comfyui_target" ]]; then
        if safe_git_update "$COMFYUI_DIR" "$comfyui_target" 2>&1; then
            comfyui_new=$(git -C "$COMFYUI_DIR" describe --tags --always 2>/dev/null || echo "$comfyui_target")
            cd "$COMFYUI_DIR" || return
            if uv pip --no-cache-dir install -r requirements.txt 2>&1; then
                # Validate PyTorch after pip install
                if [[ -n "$torch_pre" ]]; then
                    if ! validate_pytorch_version "$torch_pre" 2>&1; then
                        log "CRITICAL: PyTorch version changed after ComfyUI requirements install"
                    fi
                fi
                comfyui_status="updated"
                log "ComfyUI updated: ${comfyui_old} -> ${comfyui_new}"
            else
                comfyui_status="pip-failed"
                log "WARNING: ComfyUI pip install failed, git update was applied"
            fi
        else
            comfyui_status="git-failed"
            log "WARNING: ComfyUI update failed, continuing with current version (${comfyui_old})"
        fi
    fi
else
    comfyui_status="not-found"
    log "WARNING: ComfyUI directory not found at ${COMFYUI_DIR}"
fi

# ============================================================
# AI-Toolkit Update
# ============================================================
AI_TOOLKIT_DIR="${WORKSPACE:-/workspace}/ai-toolkit"
aitoolkit_status="skipped"
aitoolkit_old="unknown"
aitoolkit_new="unknown"

if [[ -d "$AI_TOOLKIT_DIR" ]]; then
    aitoolkit_old=$(git -C "$AI_TOOLKIT_DIR" rev-parse --short HEAD 2>/dev/null || echo "unknown")
    log "Updating AI-Toolkit (current: ${aitoolkit_old})..."

    # Determine target ref
    if [[ -n "${AI_TOOLKIT_VERSION:-}" ]]; then
        aitoolkit_target="$AI_TOOLKIT_VERSION"
        log "Using pinned AI-Toolkit version: ${aitoolkit_target}"
    else
        aitoolkit_target="origin/main"
        log "Using latest AI-Toolkit main branch"
    fi

    if safe_git_update "$AI_TOOLKIT_DIR" "$aitoolkit_target" 2>&1; then
        aitoolkit_new=$(git -C "$AI_TOOLKIT_DIR" rev-parse --short HEAD 2>/dev/null || echo "$aitoolkit_target")
        cd "$AI_TOOLKIT_DIR" || return

        # Pin timm before requirements install (known compat issue)
        if uv pip --no-cache-dir install timm==1.0.22 2>&1 && \
           uv pip --no-cache-dir install -r requirements.txt 2>&1; then

            # Validate PyTorch after pip installs
            if [[ -n "$torch_pre" ]]; then
                if ! validate_pytorch_version "$torch_pre" 2>&1; then
                    log "CRITICAL: PyTorch version changed after AI-Toolkit requirements install"
                fi
            fi

            # Rebuild Node.js UI
            if . /opt/nvm/nvm.sh 2>/dev/null && \
               cd ui && npm install 2>&1 && npm run update_db 2>&1 && npm run build 2>&1; then
                aitoolkit_status="updated"
                log "AI-Toolkit updated: ${aitoolkit_old} -> ${aitoolkit_new}"
            else
                aitoolkit_status="ui-build-failed"
                log "WARNING: AI-Toolkit UI build failed, Python packages were updated"
            fi
        else
            aitoolkit_status="pip-failed"
            log "WARNING: AI-Toolkit pip install failed, git update was applied"
        fi
    else
        aitoolkit_status="git-failed"
        log "WARNING: AI-Toolkit update failed, continuing with current version (${aitoolkit_old})"
    fi
else
    aitoolkit_status="not-found"
    log "WARNING: AI-Toolkit directory not found at ${AI_TOOLKIT_DIR}"
fi

# ============================================================
# Summary
# ============================================================
log "========================================="
log "Auto-update summary:"
log "  ComfyUI:    ${comfyui_status} (${comfyui_old} -> ${comfyui_new})"
log "  AI-Toolkit: ${aitoolkit_status} (${aitoolkit_old} -> ${aitoolkit_new})"
log "========================================="

return 0 2>/dev/null || true
