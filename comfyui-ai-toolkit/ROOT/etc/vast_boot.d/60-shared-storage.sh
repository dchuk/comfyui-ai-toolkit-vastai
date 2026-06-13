#!/bin/bash
# IMPORTANT: This script is SOURCED by boot_default.sh (not executed).
# Do NOT use `set -euo pipefail` (it propagates to the parent shell and breaks
# subsequent boot scripts). Do NOT use `exit` (use `return`).
#
# Creates the shared model tree that ComfyUI reads via
# /opt/comfyui-config/extra_model_paths.yaml. Drop a base model into
# /workspace/models/<kind>/ once and ComfyUI sees it there (in addition to its
# own /workspace/ComfyUI/models/ tree). AI-Toolkit configs can also point
# `name_or_path` at files here to avoid re-downloading. Runs after
# 36-sync-workspace.sh so /workspace exists.

shared="${WORKSPACE:-/workspace}/models"
for kind in checkpoints loras vae diffusion_models unet text_encoders clip \
            clip_vision controlnet upscale_models embeddings; do
    mkdir -p "${shared}/${kind}"
done
echo "[shared-storage] ensured shared model tree at ${shared}"
