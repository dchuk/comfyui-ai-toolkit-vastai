# `vast` — VastAI launcher for the ComfyUI + AI-Toolkit template

A small CLI that turns "I want a FLUX box" into one command: it ensures the
VastAI template exists, picks the cheapest matching GPU, launches an instance
with the right ports/env, waits until ComfyUI is actually reachable, and prints
the service URLs. It wraps the official `vastai` CLI (which it shells out to),
so it reuses your existing authentication.

## Prerequisites

```bash
pip install vastai              # the official CLI this tool wraps
vastai set api-key YOUR_API_KEY # one-time auth (see https://cloud.vast.ai/account)
```

## Install / run

Install `vast` onto your PATH (recommended — like the `vastai` CLI itself):

```bash
uv tool install ./cli          # from the repo root; gives you a `vast` command
vast --help

# After changing the CLI source, refresh the installed copy:
uv tool install ./cli --force --reinstall
```

For active development you can run straight from source instead:

```bash
uv run --project cli vast --help
```

> **Avoid `uvx --from ./cli`** for this repo: uvx caches its build by package
> version, and since this package stays at `0.1.0` during development, uvx will
> keep running a stale build and ignore your source changes. Use `uv tool
> install` or `uv run --project cli` instead.

## Usage

```bash
# Launch a FLUX-capable box, wait for ComfyUI, print URLs:
vast up flux --name my-box

# See exactly what it would do, without spending money:
vast up flux --dry-run

# Cheaper SDXL box with a hard price ceiling:
vast up sdxl --max-dph 0.30

# Pick the highest-bandwidth host instead of the cheapest (faster image pull):
vast up flux --gpu-name RTX_5090 --fastest

# Pin versions / pass extra env:
vast up flux --pin-comfyui v0.3.40 --env HF_TOKEN=hf_xxx

# Manage instances:
vast ls                 # CLI-managed instances (use --all for everything)
vast logs my-box        # boot/service logs
vast ssh my-box         # print the ssh command
vast down my-box        # destroy (confirms unless --yes)

# Back up training results before tearing a box down:
vast pull my-box                  # prompts: loras / datasets / both -> ./vast-backups/my-box/
vast pull my-box --no-datasets    # LoRAs only (explicit flag skips the prompt)
vast pull my-box --dry-run        # show the rsync commands, transfer nothing
vast pull my-box --db             # also grab the AI-Toolkit job DB + jobs/
vast down my-box                  # ...then tear down once you've verified the files

# Manage just the template:
vast template sync flux
vast template show
```

## Backing up before teardown

`vast pull <instance>` rsyncs AI-Toolkit's trained LoRAs
(`/workspace/ai-toolkit/output`) and datasets (`/workspace/ai-toolkit/datasets`)
down to `./vast-backups/<instance>/` over SSH, using the same key auto-detection
as `vast up` (`~/.ssh/id_ed25519` then `id_rsa`, or `--ssh-key <path>`). Run with
no target flag in a terminal and it prompts for **loras / datasets / both**;
pass `--outputs/--no-outputs`, `--datasets/--no-datasets`, or `--db` to choose
non-interactively (and skip the prompt). Transfers are incremental, so re-running
only fetches what changed. It never destroys anything — verify the download, then
`vast down` to stop paying for the GPU.

## Profiles

Use-case presets live in [`src/vastctl/profiles.toml`](src/vastctl/profiles.toml):
`sdxl`, `flux`, `train`. Each maps to a GPU search query, disk, and env. Override
any value at the command line, or point at your own file with `--profiles-path`.

Price is filtered client-side against each offer's `dph_total`, so the launcher
always picks the genuinely cheapest offer within your `--max-dph` budget. Pass
`--fastest` to instead select the highest internet-download-bandwidth offer
within budget (ties broken by price, then reliability) — useful when a slow host
makes the ~30 GB image pull crawl. The chosen offer's `inet_down` (Mbps) is shown
in the selection line.

## Development

```bash
cd cli
uv run pytest        # unit tests (no network — the vastai runner is mocked)
```
