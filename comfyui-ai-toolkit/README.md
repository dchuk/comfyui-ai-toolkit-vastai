# ComfyUI + AI-Toolkit VastAI Template

A Docker image combining [ComfyUI](https://github.com/Comfy-Org/ComfyUI) and [Ostris AI-Toolkit](https://github.com/ostris/ai-toolkit) into a single VastAI-deployable container. Generate images with ComfyUI and train LoRA models with AI-Toolkit — all on one GPU instance.

## What's Included

- **ComfyUI** — Node-based image/video generation interface
- **ComfyUI-Manager** — One-click custom node and model installer
- **ComfyUI API Wrapper** — REST API for programmatic access
- **AI-Toolkit** — LoRA/model training with web UI
- **Auto-Update** — Pulls latest releases on every instance boot
- **xformers & SageAttention** — Optimized attention for both tools

## Quick Start

### 1. Create a VastAI Template

In the [VastAI template editor](https://cloud.vast.ai/templates):

| Field | Value |
|-------|-------|
| **Image** | `dchuk/comfyui-ai-toolkit:latest` |
| **Ports** | `1111/http 18188/http 18288/http 8675/http 22/tcp` |
| **Disk** | 40 GB minimum (more for models) |

Or via CLI:

```bash
vastai create template \
  --name "ComfyUI + AI-Toolkit" \
  --image "dchuk/comfyui-ai-toolkit:latest" \
  --disk 40 \
  --ports "1111/http 18188/http 18288/http 8675/http 22/tcp"
```

### 2. Rent a GPU Instance

Search for an instance with your template. Recommended VRAM:

| Use Case | Minimum | Recommended |
|----------|---------|-------------|
| SD 1.5 / SDXL generation | 8 GB | 12 GB |
| FLUX generation | 16 GB | 24 GB |
| LoRA training (FLUX) | 16 GB | 24 GB |
| Video generation / training | 24 GB | 48 GB+ |

### 3. Access Your Services

Once the instance is running, click the portal buttons or use direct URLs:

| Service | Port | Description |
|---------|------|-------------|
| Instance Portal | 1111 | VastAI dashboard with service buttons |
| ComfyUI | 18188 | Node-based image generation UI |
| ComfyUI API | 18288 | REST API for ComfyUI |
| AI-Toolkit | 8675 | LoRA training web UI |

## Auto-Update System

On every instance boot, the template automatically pulls the latest versions of ComfyUI and AI-Toolkit. This means your instances stay current even if the Docker image is weeks old.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTO_UPDATE` | `true` | Set `false` to skip updates on boot |
| `COMFYUI_VERSION` | _(empty)_ | Pin ComfyUI to a release tag (e.g., `v0.3.1`) |
| `AI_TOOLKIT_VERSION` | _(empty)_ | Pin AI-Toolkit to a git ref (e.g., `6870ab4`) |
| `COMFYUI_ARGS` | `--disable-auto-launch --enable-cors-header --port 18188` | ComfyUI startup arguments |
| `AI_TOOLKIT_START_CMD` | `npm run start` | AI-Toolkit startup command |
| `WORKSPACE` | `/workspace` | Shared workspace directory |

Set these in the VastAI template's environment section, or pass them when creating an instance.

### How It Works

1. `70-auto-update.sh` runs via VastAI's `vast_boot.d` hook before services start
2. ComfyUI is checked out to the latest GitHub release tag (or `COMFYUI_VERSION` if set)
3. AI-Toolkit is pulled to latest `origin/main` (or `AI_TOOLKIT_VERSION` if set)
4. Python dependencies are reinstalled and PyTorch version is validated
5. On failure, the baked-in version keeps running — updates never block startup

## Building from Source

### CI Pipeline (Recommended)

The GitHub Actions workflow builds and pushes automatically on every push to `main`. To set it up:

1. Fork or clone this repo
2. Add three repository secrets in **Settings > Secrets and variables > Actions**:

   | Secret | Value |
   |--------|-------|
   | `DOCKERHUB_USERNAME` | Your Docker Hub username |
   | `DOCKERHUB_TOKEN` | A Docker Hub [access token](https://hub.docker.com/settings/security) |
   | `DOCKERHUB_NAMESPACE` | Your Docker Hub username or org |

3. Push to `main` — the pipeline runs: **lint** (shellcheck + hadolint) > **preflight** (secret check) > **build-and-push**

The image is pushed as `{DOCKERHUB_NAMESPACE}/comfyui-ai-toolkit:latest` and `:{sha}`.

### Local Build

```bash
cd comfyui-ai-toolkit

# Basic build (local image only)
./build.sh

# Build and push to your registry
DOCKER_REGISTRY=your-username ./build.sh --push
```

Requires ~30 GB free disk space and Docker with buildx.

## Service Management

All services run under supervisord:

```bash
# Check service status
supervisorctl status

# Restart a service
supervisorctl restart comfyui
supervisorctl restart api-wrapper
supervisorctl restart ai-toolkit

# Follow service logs
supervisorctl tail -f comfyui
supervisorctl tail -f ai-toolkit
```

## Directory Structure

```
/workspace/
├── ComfyUI/                  # ComfyUI installation
│   ├── models/               # Model storage
│   │   ├── checkpoints/      # SD/FLUX/etc. models
│   │   ├── loras/            # LoRA files
│   │   ├── vae/              # VAE models
│   │   ├── controlnet/       # ControlNet models
│   │   └── ckpt -> checkpoints  # Symlink (Jupyter compat)
│   ├── custom_nodes/
│   │   └── ComfyUI-Manager/  # Pre-installed
│   └── output/               # Generated images
└── ai-toolkit/               # AI-Toolkit installation
    ├── output/               # Trained models
    └── ui/                   # Web UI (Node.js)

/opt/
├── comfyui-api-wrapper/      # API wrapper (separate venv)
└── supervisor-scripts/       # Service startup scripts
    └── utils/
        └── update.sh         # Auto-update functions
```

## Base Image

Built on `vastai/pytorch:2.9.1-cu128-cuda-12.9-mini-py312` which provides:

- PyTorch 2.9.1 with CUDA 12.9
- Python 3.12 with uv package manager
- Node.js via nvm
- Supervisord, Caddy, JupyterLab
- VastAI Instance Portal framework

## Troubleshooting

### Service won't start

```bash
# Check all service status
supervisorctl status

# View full logs for a service
supervisorctl tail -f comfyui
```

### Auto-update failed

Check the boot log — auto-update failures are logged but never block startup:

```bash
# View boot logs
cat /var/log/vast_boot.log
```

To skip updates temporarily, set `AUTO_UPDATE=false` in the VastAI template environment.

### PyTorch/CUDA issues

```bash
# Verify GPU access
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}, Device: {torch.cuda.get_device_name(0)}')"
```

### Dependency conflicts

ComfyUI and AI-Toolkit share the same Python venv. If you install conflicting packages (e.g., via ComfyUI-Manager custom nodes), one tool may break. Test after installing new custom nodes.

### Disk space

CUDA images are large. If you run out of space, check:

```bash
df -h /workspace
du -sh /workspace/ComfyUI/models/*
```

## License

This template combines multiple open-source projects:
- [ComfyUI](https://github.com/Comfy-Org/ComfyUI) — GPL-3.0
- [AI-Toolkit](https://github.com/ostris/ai-toolkit) — Apache-2.0
- [ComfyUI API Wrapper](https://github.com/ai-dock/comfyui-api-wrapper) — See repo
- [VastAI Base Images](https://github.com/vast-ai/base-image) — Various
