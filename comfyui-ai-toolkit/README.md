# Combined ComfyUI + AI-Toolkit VastAI Template

A Docker image that combines [ComfyUI](https://github.com/Comfy-Org/ComfyUI) and [Ostris AI-Toolkit](https://github.com/ostris/ai-toolkit) into a single VastAI-compatible template.

## Features

- **ComfyUI** - Node-based stable diffusion interface for image generation
- **ComfyUI-Manager** - Pre-installed for easy custom node management
- **ComfyUI API Wrapper** - REST API for programmatic ComfyUI access
- **AI-Toolkit** - LoRA/model training with web UI
- **Shared Environment** - Both tools share PyTorch/CUDA stack for efficiency
- **xformers & SageAttention** - Optimized attention mechanisms for both tools

## Port Assignments

| Service | Internal Port | External Port | Description |
|---------|---------------|---------------|-------------|
| Portal | 11111 | 1111 | VastAI portal interface |
| Jupyter | 8080 | 8080 | JupyterLab |
| ComfyUI | 18188 | 8188 | ComfyUI web interface |
| ComfyUI API | 18288 | 8288 | ComfyUI REST API |
| AI Toolkit | 8675 | 18675 | AI-Toolkit web UI |

## Building

### Quick Build

```bash
./build.sh
```

### Custom Build

```bash
# Set your DockerHub username
export DOCKER_REGISTRY=your-username

# Build with specific versions
export COMFYUI_REF=v0.3.0
export AI_TOOLKIT_REF=6870ab4

./build.sh
```

### Manual Build

```bash
docker buildx build \
    --build-arg COMFYUI_REF=v0.3.0 \
    --build-arg AI_TOOLKIT_REF=6870ab4 \
    -t your-username/comfyui-ai-toolkit:latest \
    .
```

## Publishing

```bash
# Push to Docker Hub
docker push your-username/comfyui-ai-toolkit:latest
```

## Usage on VastAI

1. Build and push the image to Docker Hub (or another registry)
2. Create a new VastAI template using your image tag
3. Configure port mappings as needed:
   - 8188 -> 18188 (ComfyUI)
   - 8288 -> 18288 (ComfyUI API)
   - 18675 -> 8675 (AI Toolkit)
4. Launch an instance

## Service Management

All services are managed via supervisord. Common commands:

```bash
# Check status of all services
supervisorctl status

# Restart a specific service
supervisorctl restart comfyui
supervisorctl restart api-wrapper
supervisorctl restart ai-toolkit

# View logs
supervisorctl tail -f comfyui
supervisorctl tail -f ai-toolkit
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `COMFYUI_ARGS` | `--disable-auto-launch --enable-cors-header --port 18188` | ComfyUI startup arguments |
| `AI_TOOLKIT_START_CMD` | `npm run start` | AI-Toolkit startup command |
| `WORKSPACE` | `/workspace` | Shared workspace directory |

## Directory Structure

On the running instance:

```
/workspace/
├── ComfyUI/               # ComfyUI installation
│   ├── models/            # Model storage
│   │   ├── checkpoints/
│   │   ├── loras/
│   │   └── ...
│   └── custom_nodes/      # Custom nodes
│       └── ComfyUI-Manager/
└── ai-toolkit/            # AI-Toolkit installation
    └── ui/                # Web UI

/opt/
├── comfyui-api-wrapper/   # API wrapper (separate venv)
└── nvm/                   # Node.js for AI-Toolkit
```

## Base Image

This image extends `vastai/pytorch:2.9.1-cu128-cuda-12.9-mini-py312` which includes:

- PyTorch 2.9.1
- CUDA 12.9
- Python 3.12
- VastAI base utilities (portal, jupyter, supervisord)

## Troubleshooting

### Service won't start

Check supervisor logs:
```bash
supervisorctl tail -f [service-name]
```

### PyTorch/CUDA issues

Verify GPU access:
```bash
python -c "import torch; print(torch.cuda.is_available())"
```

### Dependency conflicts

Both tools share the same Python environment. If you install conflicting packages, one tool may break. Use the ComfyUI-Manager carefully and test after installing new custom nodes.

## Version Compatibility

| Component | Version | Notes |
|-----------|---------|-------|
| PyTorch | 2.9.1 | Locked by base image |
| ComfyUI | v0.3.0 | Configurable via build arg |
| AI-Toolkit | 6870ab4 | Configurable via build arg |
| timm | 1.0.22 | Pinned for AI-Toolkit compatibility |
| xformers | Latest | Installed for performance |
| sageattention | 1.0.6 | Installed for performance |

## License

This template combines multiple open-source projects. See individual project licenses:
- ComfyUI: GPL-3.0
- AI-Toolkit: Apache-2.0
- VastAI base images: Various
