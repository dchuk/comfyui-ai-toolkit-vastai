# Combined ComfyUI + AI-Toolkit VastAI Template
# Based on VastAI PyTorch base image with both tools installed

ARG PYTORCH_BASE=vastai/pytorch:2.9.1-cu128-cuda-12.9-mini-py312

FROM ${PYTORCH_BASE}

# Maintainer details
LABEL org.opencontainers.image.source="https://github.com/vastai/"
LABEL org.opencontainers.image.description="Combined ComfyUI and AI-Toolkit image for Vast.ai"
LABEL maintainer="Custom build"

# ============================================================
# Dependency Versions (all git clones pinned for reproducibility)
# ============================================================
# ComfyUI:         ${COMFYUI_REF}         (release tag)
# ComfyUI-Manager: ${COMFYUI_MANAGER_REF} (release tag)
# API Wrapper:     ${API_WRAPPER_REF}      (commit hash)
# AI-Toolkit:      ${AI_TOOLKIT_REF}       (commit hash)
# xformers:        unpinned (binary-matched to torch via --torch-backend)
# sageattention:   1.0.6
# timm:            1.0.22
# Base image:      vastai/pytorch:2.9.1-cu128-cuda-12.9-mini-py312

# Copy Supervisor configuration and startup scripts
COPY ./ROOT /

# ============================================================
# ComfyUI Installation
# ============================================================
ARG COMFYUI_REF=v0.3.0
ARG COMFYUI_MANAGER_REF=4.0.5

RUN \
    set -euo pipefail && \
    [[ -n "${COMFYUI_REF}" ]] || { echo "Must specify COMFYUI_REF" && exit 1; } && \
    . /venv/main/bin/activate && \
    # We have PyTorch pre-installed so we will check at the end of the install that it has not been clobbered
    torch_version_pre="$(python -c 'import torch; print (torch.__version__)')" && \
    # Install xformers and sageattention (benefits both ComfyUI and AI-Toolkit)
    uv pip install --no-cache-dir torch=="${PYTORCH_VERSION}" xformers sageattention==1.0.6 --torch-backend "${PYTORCH_BACKEND}" && \
    # Get ComfyUI and install dependencies
    cd /opt/workspace-internal/ && \
    git clone https://github.com/Comfy-Org/ComfyUI && \
    cd /opt/workspace-internal/ComfyUI && \
    git checkout "${COMFYUI_REF}" && \
    uv pip install --no-cache-dir -r requirements.txt && \
    # Avoid Jupyter directory display bug
    cd /opt/workspace-internal/ComfyUI/models/ && \
    ln -s checkpoints ckpt && \
    # Install ComfyUI-Manager
    cd /opt/workspace-internal/ComfyUI/custom_nodes && \
    git clone https://github.com/Comfy-Org/ComfyUI-Manager && \
    cd ComfyUI-Manager && \
    git checkout "${COMFYUI_MANAGER_REF}" && \
    cd .. && \
    uv pip install --no-cache-dir -r ComfyUI-Manager/requirements.txt && \
    # Quick startup test in CPU mode
    cd /opt/workspace-internal/ComfyUI && \
    LD_PRELOAD=libtcmalloc_minimal.so.4 \
         python main.py \
            --cpu \
            --listen 127.0.0.1 \
            --port 11404 \
            --disable-auto-launch \
            --quick-test-for-ci && \
    mkdir -p /opt/workspace-internal/ComfyUI/user/default/ComfyUI-Manager/components && \
    # Verify PyTorch version is unaltered
    torch_version_post="$(python -c 'import torch; print (torch.__version__)')" && \
    [[ $torch_version_pre = $torch_version_post ]] || { echo "PyTorch version mismatch (wanted ${torch_version_pre} but got ${torch_version_post})"; exit 1; }

ENV COMFYUI_ARGS="--disable-auto-launch --enable-cors-header --port 18188"

# ============================================================
# ComfyUI API Wrapper Installation
# ============================================================
ARG API_WRAPPER_REF=5b6a181

RUN \
    set -euo pipefail && \
    apt-get update && \
    apt-get install -y --no-install-recommends libmagic1 && \
    cd /opt && \
    git clone https://github.com/ai-dock/comfyui-api-wrapper && \
    cd comfyui-api-wrapper && \
    git checkout "${API_WRAPPER_REF}" && \
    uv venv -p 3.12 && \
    . .venv/bin/activate && \
    uv pip install -r requirements.txt && \
    deactivate && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# ============================================================
# AI-Toolkit Installation
# ============================================================
ARG AI_TOOLKIT_REPO=https://github.com/ostris/ai-toolkit
ARG AI_TOOLKIT_REF=6870ab4

RUN \
    set -euo pipefail && \
    [[ -n "${AI_TOOLKIT_REF}" ]] || { echo "Must specify AI_TOOLKIT_REF"; exit 1; } && \
    . /venv/main/bin/activate && \
    . /opt/nvm/nvm.sh && \
    # Record PyTorch version before install
    torch_version_pre="$(python -c 'import torch; print (torch.__version__)')" && \
    cd /opt/workspace-internal && \
    git clone "${AI_TOOLKIT_REPO}" && \
    cd ai-toolkit && \
    git checkout "${AI_TOOLKIT_REF}" && \
    # Fix known issue with toolkit 6870ab4 - pin timm before requirements install
    uv pip install --no-cache-dir timm==1.0.22 && \
    uv pip install --no-cache-dir -r requirements.txt && \
    # Build Node.js UI
    cd ui && \
    npm install && \
    npm run update_db && \
    npm run build && \
    # Verify PyTorch version is unaltered
    torch_version_post="$(python -c 'import torch; print (torch.__version__)')" && \
    [[ $torch_version_pre = $torch_version_post ]] || { echo "PyTorch version mismatch (wanted ${torch_version_pre} but got ${torch_version_post})"; exit 1; }

# ============================================================
# Auto-Update Configuration
# ============================================================
# AUTO_UPDATE: Set to "false" to disable auto-update on instance startup
# COMFYUI_VERSION: Pin ComfyUI to a specific release tag (e.g., "v0.3.1"). Empty = latest release.
# AI_TOOLKIT_VERSION: Pin AI-Toolkit to a specific ref (e.g., "6870ab4"). Empty = latest main branch.
ENV AUTO_UPDATE=true

# ============================================================
# Optional: Include SD 1.5 model for testing/benchmarking
# Uncomment if needed - adds ~2GB to image size
# ============================================================
# RUN \
#     set -euo pipefail && \
#     mkdir -p /opt/model_store && \
#     . /venv/main/bin/activate && \
#     hf download Comfy-Org/stable-diffusion-v1-5-archive v1-5-pruned-emaonly-fp16.safetensors \
#         --local-dir "/opt/model_store" && \
#     ln -s /opt/model_store/v1-5-pruned-emaonly-fp16.safetensors \
#         /opt/workspace-internal/ComfyUI/models/checkpoints/v1-5-pruned-emaonly-fp16.safetensors && \
#     rm -rf /opt/model_store/.cache && \
#     rm -rf /root/.cache/huggingface

# ============================================================
# Portal Configuration
# ============================================================
# Configure the VastAI portal to show our applications
# Portal Configuration: format is hostname:external_port:internal_port:path:name
# external_port = what Caddy listens on (must match ports exposed in VastAI template)
# internal_port = where the actual application runs inside the container
# When external_port == internal_port, Caddy skips proxying (direct access)
# Service names must match what exit_portal.sh looks for in each startup script
# Template ports should be: 1111, 18188, 18288, 8675
ENV PORTAL_CONFIG="localhost:1111:11111:/:Instance Portal|localhost:18188:18188:/:ComfyUI|localhost:18288:18288:/:API Wrapper|localhost:8675:8675:/:AI Toolkit"

# ============================================================
# Finalize
# ============================================================
# Defend against environment clashes when syncing to volume
RUN \
    set -euo pipefail && \
    env-hash > /.env_hash
