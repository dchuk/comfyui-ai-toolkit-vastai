# ComfyUI + AI-Toolkit VastAI Template

A Docker image combining [ComfyUI](https://github.com/Comfy-Org/ComfyUI) and [Ostris AI-Toolkit](https://github.com/ostris/ai-toolkit) into a single VastAI-deployable container. Generate images with ComfyUI and train LoRA models with AI-Toolkit — all on one GPU instance.

## What's Included

- **ComfyUI** — Node-based image/video generation interface
- **ComfyUI-Manager** — One-click custom node and model installer
- **ComfyUI API Wrapper** — REST API for programmatic access
- **AI-Toolkit** — LoRA/model training with web UI
- **Jupyter** — Browser-based file manager, notebooks, and terminal (port 8080)
- **Auto-Update** — Pulls latest releases on every instance boot
- **xformers & SageAttention** — Optimized attention for both tools

## Quick Start

The fastest path is the bundled **[`vast` CLI](../cli/README.md)** — it creates/updates the template, rents the cheapest matching GPU, waits until ComfyUI is reachable, and prints the service URLs, all in one command:

```bash
# one-time: install the `vast` command (requires the official vastai CLI, authenticated via `vastai set api-key`)
uv tool install ./cli

vast up flux --name my-box      # profiles: sdxl / flux / train
vast up flux --dry-run          # preview the plan without spending money
```

Profiles, price ceilings (`--max-dph`), version pinning (`--pin-comfyui`), and lifecycle commands (`vast ls` / `logs` / `ssh` / `down`) are documented in **[`cli/README.md`](../cli/README.md)**.

Prefer to set it up by hand? Follow the manual steps below.

### 1. Create a VastAI Template

In the [VastAI template editor](https://cloud.vast.ai/templates):

| Field | Value |
|-------|-------|
| **Image** | `dchuk/comfyui-ai-toolkit:latest` |
| **Ports** | `1111/http 18189/http 18288/http 8675/http 8080/http 22/tcp` |
| **Disk** | 40 GB minimum (more for models) |
| **Launch Mode** | **Docker ENTRYPOINT / `args`** — *not* SSH or Jupyter |

> **Critical — launch mode:** this image manages its own services (supervisor →
> Caddy, ComfyUI, API wrapper, AI-Toolkit) from its ENTRYPOINT, and provides SSH
> itself. It **must** run in **entrypoint/args mode**. If you launch it as an
> **SSH** (or Jupyter) instance, VastAI runs an ssh-only container and the web
> services never start — the portal and ComfyUI URLs will refuse to connect.
>
> The VastAI console "RENT" button launches a template in SSH mode by default
> and there's no template flag to change that, so **the bundled
> [`vast` CLI](../cli/README.md) is the reliable way to launch this image** — it
> forces entrypoint/args mode (and authorizes your SSH key automatically). Use
> the manual console path only if you set the launch mode to ENTRYPOINT yourself.

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
| ComfyUI | 18189 | Node-based image generation UI (auth-proxied via Caddy to internal 18188) |
| ComfyUI API | 18288 | REST API for ComfyUI |
| AI-Toolkit | 8675 | LoRA training web UI |
| Jupyter | 8080 | Browser file manager, notebooks, and terminal (proxied via Caddy on internal 18080) |

### Access & authentication

The Instance Portal (1111) and the **ComfyUI** tile (18189) are served **through
the portal's Caddy**, which protects them with the portal's auth stack: HTTP
**basic auth** (username `vastai`) plus token / cookie / bearer auth. Opening a
service from the portal's blue **Open** button passes a one-time `?token=`, which
sets an auth cookie — so you're logged in seamlessly and never see a password
prompt. Hitting a service URL **directly** (e.g. bookmarking the ComfyUI URL)
triggers the basic-auth prompt instead.

- **Why ComfyUI is proxied:** ComfyUI binds loopback (`127.0.0.1:18188`), so it
  has no usable direct Vast port and would otherwise be reachable only through a
  flaky cloudflare quick-tunnel. Exposing it on **18189** with Caddy in front
  gives it a **stable, authenticated** URL. ComfyUI is never bound to a public
  interface.
- **Password:** defaults to the per-instance `OPEN_BUTTON_TOKEN` (auto-generated
  by VastAI). Set `WEB_PASSWORD` (and optionally `WEB_USERNAME`) as instance env
  to choose your own credentials for direct access.
- **Opt out:** set `AUTH_EXCLUDE=18189` (comma-separated port list) to serve
  ComfyUI without auth.

## Auto-Update System

On every instance boot, the template automatically pulls the latest versions of ComfyUI and AI-Toolkit. This means your instances stay current even if the Docker image is weeks old.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTO_UPDATE` | `true` | Set `false` to skip updates on boot |
| `COMFYUI_VERSION` | _(empty)_ | Pin ComfyUI to a release tag (e.g., `v0.3.1`) |
| `AI_TOOLKIT_VERSION` | _(empty)_ | Pin AI-Toolkit to a git ref (e.g., `6870ab4`) |
| `COMFYUI_ARGS` | `--disable-auto-launch --enable-cors-header --port 18188 --enable-manager --enable-manager-legacy-ui` | ComfyUI startup arguments (`--enable-manager` turns on ComfyUI-Manager; `--enable-manager-legacy-ui` loads the classic UI with the full Model Manager) |
| `AI_TOOLKIT_START_CMD` | `npm run start` | AI-Toolkit startup command |
| `WEB_USERNAME` | `vastai` | Basic-auth username for Caddy-proxied services (portal, ComfyUI) |
| `WEB_PASSWORD` | _(per-instance token)_ | Basic-auth password; defaults to the auto-generated `OPEN_BUTTON_TOKEN`. Set to choose your own |
| `AUTH_EXCLUDE` | _(empty)_ | Comma-separated external ports to serve **without** auth (e.g. `18189` for ComfyUI) |
| `WORKSPACE` | `/workspace` | Shared workspace directory |

Set these in the VastAI template's environment section, or pass them when creating an instance.

### How It Works

1. `70-auto-update.sh` runs via VastAI's `vast_boot.d` hook before services start
2. ComfyUI is checked out to the latest GitHub release tag (or `COMFYUI_VERSION` if set)
3. AI-Toolkit is pulled to latest `origin/main` (or `AI_TOOLKIT_VERSION` if set)
4. Python dependencies are reinstalled and PyTorch version is validated
5. On failure, the baked-in version keeps running — updates never block startup

## Shared Model Storage

ComfyUI and AI-Toolkit each manage models differently, so the template shares
what it usefully can without duplicating files:

- **Trained LoRAs appear in ComfyUI automatically.** AI-Toolkit writes LoRAs to
  `/workspace/ai-toolkit/output/<job-id>/`, and ComfyUI is configured to read
  that directory as a LoRA source. After a training run finishes, the LoRA shows
  up in ComfyUI's LoRA loader as `<job-id>/<name>.safetensors` — no copy needed.
- **A shared `/workspace/models/` tree.** Drop a base model into the matching
  subdirectory once (e.g. `/workspace/models/checkpoints/`,
  `/workspace/models/loras/`) and ComfyUI sees it there, in addition to its own
  `/workspace/ComfyUI/models/` tree. To use the same file in an AI-Toolkit
  training run, point that job's `name_or_path` at the file's path.
- **HuggingFace cache persists.** `HF_HOME=/workspace/.hf_home` lives on the
  instance volume, so base models AI-Toolkit pulls from HuggingFace are not
  re-downloaded across restarts of the same instance.

This is wired via ComfyUI's native `--extra-model-paths-config`
(`/opt/comfyui-config/extra_model_paths.yaml`); the boot hook
`60-shared-storage.sh` creates the `/workspace/models/` directories on first boot.

**What is *not* de-duplicated:** base models for *training* vs *inference* are
genuinely different artifacts — AI-Toolkit needs the multi-file HuggingFace
diffusers repo, while ComfyUI needs a single-file safetensors checkpoint — so a
model used for both will exist in both forms.

## Downloading models

ComfyUI has two different "Download" buttons and **only one saves to the server** —
important to know on a remote rented box.

### Which button does what

- **The native *Missing Models* panel** (the dialog that pops up when you open a
  workflow referencing models you don't have) downloads **to your local
  computer**, not the server. This is ComfyUI frontend behavior — it triggers a
  browser download — so on a remote instance the file ends up on your laptop, not
  the GPU box. Use this panel only to grab each model's **Copy URL**, then pull it
  onto the server (see *Manually* below).
- **ComfyUI-Manager → Model Manager** downloads **to the server**. This is the
  official in-UI server-side path. Open the **Manager** (button in the top
  toolbar), open **Install Models / Model Manager**, search for a model, and click
  **Install** — it downloads straight into `/workspace/ComfyUI/models/<type>/` on
  the persistent volume. It covers models in the Manager's curated database;
  arbitrary workflow-specific files it doesn't know about won't appear there
  (download those manually).

  > The Model Manager only appears in the **classic** Manager UI, so the image
  > launches ComfyUI with `--enable-manager-legacy-ui` (see `COMFYUI_ARGS`). The
  > newer default Manager UI does not expose an arbitrary-model installer. Drop
  > `--enable-manager-legacy-ui` from `COMFYUI_ARGS` if you prefer the new UI.

The Model Manager (and Manager node installs) work out of the box because the
image ships `network_mode = personal_cloud` with `security_level = normal` in
`/workspace/ComfyUI/user/__manager/config.ini`:

- ComfyUI binds `127.0.0.1` and VastAI proxies external traffic to it. Without
  `personal_cloud`, ComfyUI-Manager treats the proxied connection as an untrusted
  remote and **blocks** server-side installs with a "this request is banned" or
  "not allowed with this security level" error. `personal_cloud` is the documented
  exception for self-hosted cloud GPUs.
- `security_level` stays `normal`, so installing **arbitrary** git-URL or pip
  packages is still gated (curated downloads from the Manager database are
  allowed). Raise it to `normal-` or `weak` in that file only if you accept the
  risk, then `supervisorctl restart comfyui`.
- **Gated HuggingFace repos** (some FLUX / Ideogram weights) need auth. Launch
  with a token so the downloader can reach them:
  `vast up flux --env HF_TOKEN=hf_xxx`.

### Manually (works for any model)

The most reliable path for arbitrary workflow models: copy the URL from the
*Missing Models* panel, then download it **on the server** into the shared
`/workspace/models/` tree (or ComfyUI's own `/workspace/ComfyUI/models/`).
ComfyUI picks it up after you **Refresh** the model lists — no restart needed.
Run these from the **Jupyter terminal** (port 8080) or over SSH:

```bash
# on the instance — pick the dir matching the model type
wget -P /workspace/models/diffusion_models/ "<paste Copy-URL here>"
wget -P /workspace/models/loras/           "<url>"
wget -P /workspace/models/vae/             "<url>"

# gated HuggingFace repos (needs HF_TOKEN in the environment)
hf download <repo> <file> --local-dir /workspace/models/text_encoders/

# or push a local file up from your machine
scp my-lora.safetensors root@<host>:/workspace/models/loras/   # host/port from `vast ssh <instance>`
```

See [Shared Model Storage](#shared-model-storage) above for the full layout.

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
├── models/                   # SHARED model tree (visible to ComfyUI, see below)
│   ├── checkpoints/  loras/  vae/  diffusion_models/  unet/
│   ├── text_encoders/  clip/  clip_vision/  controlnet/
│   └── upscale_models/  embeddings/
├── .hf_home/                 # HuggingFace cache (HF_HOME) — AI-Toolkit base models
├── ComfyUI/                  # ComfyUI installation
│   ├── models/               # ComfyUI's own model tree (also read; additive to /workspace/models)
│   │   ├── checkpoints/      # SD/FLUX/etc. models
│   │   ├── loras/            # LoRA files
│   │   ├── vae/              # VAE models
│   │   ├── controlnet/       # ControlNet models
│   │   └── ckpt -> checkpoints  # Symlink (Jupyter compat)
│   ├── custom_nodes/         # Your custom nodes (ComfyUI-Manager is a pip package, not here)
│   ├── user/__manager/config.ini  # ComfyUI-Manager config (network_mode=personal_cloud)
│   └── output/               # Generated images
└── ai-toolkit/               # AI-Toolkit installation
    ├── output/               # Trained LoRAs (per-job dirs) — also shown in ComfyUI
    ├── datasets/             # Training datasets (uploaded via the UI)
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
