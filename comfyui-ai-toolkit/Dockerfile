# Combined ComfyUI + AI-Toolkit VastAI Template
# Based on VastAI PyTorch base image with both tools installed

ARG PYTORCH_BASE=vastai/pytorch:2.9.1-cu128-cuda-12.9-mini-py312

FROM ${PYTORCH_BASE}

# Maintainer details
LABEL org.opencontainers.image.source="https://github.com/vastai/"
LABEL org.opencontainers.image.description="Combined ComfyUI and AI-Toolkit image for Vast.ai"
LABEL maintainer="Custom build"

# Use bash for RUN commands (tells hadolint/shellcheck to apply bash rules, not POSIX sh)
SHELL ["/bin/bash", "-c"]

# ============================================================
# ComfyUI Installation
# ============================================================
RUN \
    set -euo pipefail && \
    . /venv/main/bin/activate && \
    # We have PyTorch pre-installed so we will check at the end of the install that it has not been clobbered
    torch_version_pre="$(python -c 'import torch; print (torch.__version__)')" && \
    # Install xformers and sageattention (benefits both ComfyUI and AI-Toolkit)
    uv pip install --no-cache-dir torch=="${PYTORCH_VERSION}" xformers sageattention==1.0.6 --torch-backend "${PYTORCH_BACKEND}" && \
    # Get ComfyUI and install dependencies
    cd /opt/workspace-internal/ && \
    git clone https://github.com/Comfy-Org/ComfyUI && \
    cd /opt/workspace-internal/ComfyUI && \
    uv pip install --no-cache-dir -r requirements.txt && \
    # Avoid Jupyter directory display bug
    cd /opt/workspace-internal/ComfyUI/models/ && \
    ln -s checkpoints ckpt && \
    # Install ComfyUI-Manager. ComfyUI v0.24+ ships built-in manager support
    # gated behind --enable-manager (see COMFYUI_ARGS below) and loads it from
    # the `comfyui-manager` PyPI package rather than a custom_nodes clone. The
    # package is only published as a prerelease, hence --pre. No -U: installing
    # without upgrade keeps the torch/transformers pins from ComfyUI's
    # requirements.txt above intact (a bare -U drags the whole ML stack forward).
    uv pip install --no-cache-dir --pre comfyui-manager && \
    # Seed ComfyUI-Manager config. network_mode=personal_cloud authorizes model
    # downloads and curated node installs from the Manager UI. ComfyUI binds
    # loopback and VastAI proxies external traffic to it, so without this the
    # Manager sees the proxied client IPs as untrusted remotes and blocks installs
    # ("This request is banned" / security_level errors). security_level stays
    # "normal" so arbitrary git-url / pip installs remain gated. read_config()
    # preserves these keys and fills the rest with defaults on first run.
    mkdir -p /opt/workspace-internal/ComfyUI/user/__manager && \
    printf '[default]\nsecurity_level = normal\nnetwork_mode = personal_cloud\n' \
        > /opt/workspace-internal/ComfyUI/user/__manager/config.ini && \
    # Quick startup test in CPU mode
    cd /opt/workspace-internal/ComfyUI && \
    LD_PRELOAD=libtcmalloc_minimal.so.4 \
         python main.py \
            --cpu \
            --listen 127.0.0.1 \
            --port 11404 \
            --disable-auto-launch \
            --quick-test-for-ci && \
    # Verify PyTorch version is unaltered
    torch_version_post="$(python -c 'import torch; print (torch.__version__)')" && \
    [[ "$torch_version_pre" = "$torch_version_post" ]] || { echo "PyTorch version mismatch (wanted ${torch_version_pre} but got ${torch_version_post})"; exit 1; }

# --enable-manager turns on ComfyUI's built-in ComfyUI-Manager (the comfyui-manager
# package installed above). Without it, loading a workflow that references custom
# nodes prompts the user to install the manager manually.
# --enable-manager-legacy-ui loads the classic Manager UI, which exposes the full
# Model Manager (search + server-side Install + paste-a-URL) and Custom Nodes
# Manager. The newer default UI does not surface an arbitrary-URL model installer.
ENV COMFYUI_ARGS="--disable-auto-launch --enable-cors-header --port 18188 --enable-manager --enable-manager-legacy-ui"

# ============================================================
# ComfyUI API Wrapper Installation
# ============================================================
RUN \
    set -euo pipefail && \
    apt-get update && \
    apt-get install -y --no-install-recommends libmagic1 && \
    cd /opt && \
    git clone https://github.com/ai-dock/comfyui-api-wrapper && \
    cd comfyui-api-wrapper && \
    uv venv -p 3.12 && \
    . .venv/bin/activate && \
    uv pip install -r requirements.txt && \
    deactivate && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# ============================================================
# AI-Toolkit Installation
# ============================================================
RUN \
    set -euo pipefail && \
    . /venv/main/bin/activate && \
    . /opt/nvm/nvm.sh && \
    # Record PyTorch version before install
    torch_version_pre="$(python -c 'import torch; print (torch.__version__)')" && \
    cd /opt/workspace-internal && \
    git clone https://github.com/ostris/ai-toolkit && \
    cd ai-toolkit && \
    uv pip install --no-cache-dir timm==1.0.22 && \
    uv pip install --no-cache-dir -r requirements.txt && \
    # Build Node.js UI
    cd ui && \
    npm install && \
    npm run update_db && \
    npm run build && \
    # Verify PyTorch version is unaltered
    torch_version_post="$(python -c 'import torch; print (torch.__version__)')" && \
    [[ "$torch_version_pre" = "$torch_version_post" ]] || { echo "PyTorch version mismatch (wanted ${torch_version_pre} but got ${torch_version_post})"; exit 1; }

# ============================================================
# Auto-Update Configuration
# ============================================================
# AUTO_UPDATE: Set to "false" to disable auto-update on instance startup
# COMFYUI_VERSION: Pin ComfyUI to a specific release tag (e.g., "v0.3.1"). Empty = latest release.
# AI_TOOLKIT_VERSION: Pin AI-Toolkit to a specific ref (e.g., "6870ab4"). Empty = latest main branch.
ENV AUTO_UPDATE=true

# ============================================================
# SSH Server
# ============================================================
# The "mini" base image lacks openssh-server, and entrypoint/args launch mode
# does not get VastAI's injected sshd. Install it so our supervisor-managed
# sshd (supervisor-scripts/sshd.sh) can run for remote access/debugging.
RUN \
    set -euo pipefail && \
    apt-get update && \
    apt-get install -y --no-install-recommends openssh-server && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

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
# Template ports should be: 1111, 18188, 18288, 8675, 8080
# Jupyter: the base image's jupyter service self-exits unless "jupyter" appears
# in PORTAL_CONFIG. In entrypoint mode it then runs PROXIED through Caddy (auth
# via the portal, no token) on internal 18080, exposed externally on 8080. The
# second entry is a deep-link tile to Jupyter's browser terminal.
ENV PORTAL_CONFIG="localhost:1111:11111:/:Instance Portal|localhost:18188:18188:/:ComfyUI|localhost:18288:18288:/:API Wrapper|localhost:8675:8675:/:AI Toolkit|localhost:8080:18080:/:Jupyter|localhost:8080:8080:/terminals/1:Jupyter Terminal"

# Point VastAI's blue "Open" button at the Instance Portal (port 1111) instead
# of defaulting to the SSH interface. OPEN_BUTTON_TOKEN is auto-generated by VastAI.
ENV OPEN_BUTTON_PORT=1111

# ============================================================
# Supervisor Configuration & Startup Scripts
# ============================================================
# Placed late so edits to scripts don't invalidate heavy install layers above
COPY ./ROOT /

# ============================================================
# Finalize
# ============================================================
# Defend against environment clashes when syncing to volume
RUN \
    set -euo pipefail && \
    env-hash > /.env_hash
