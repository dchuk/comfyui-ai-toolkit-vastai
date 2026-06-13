---
description: Launch the ComfyUI + AI-Toolkit template on VastAI via the vast CLI
argument-hint: <profile> [--name X] [--max-dph 0.30] [--dry-run] [extra vast up flags]
allowed-tools: Bash(vast*), Bash(uv run --project cli vast*), Bash(cd*)
---

Launch (or plan) a VastAI instance of this repo's ComfyUI + AI-Toolkit template
using the project's `vast` CLI. The CLI holds all the logic (template sync,
cheapest-offer selection, readiness wait, URL printing); this command is just a
convenient front door.

Arguments: `$ARGUMENTS` (a profile name like `sdxl`/`flux`/`train`, optionally
followed by flags such as `--name`, `--max-dph`, `--pin-comfyui`, `--dry-run`).

Steps:

1. Run the installed CLI with the user's arguments:

   ```bash
   vast up $ARGUMENTS
   ```

   If `vast` is not on PATH, install it first with `uv tool install ./cli` (or
   run from source with `uv run --project cli vast up $ARGUMENTS`). Do **not**
   use `uvx --from ./cli` — it caches a stale build for this unversioned package.

2. If the user did not clearly intend a real (paid) launch, prefer adding
   `--dry-run` first and show them the planned `vastai` commands before doing a
   live launch. A live launch rents a GPU and costs money.

3. Relay the CLI output: the selected offer, the instance id, and the printed
   service URLs (ComfyUI / API / AI-Toolkit / Portal) and SSH command.

4. For follow-ups, use the sibling commands: `vast ls`, `vast logs <ref>`,
   `vast ssh <ref>`, `vast down <ref>`.

Prerequisite: the official `vastai` CLI must be installed and authenticated
(`vastai set api-key ...`). If the CLI reports a preflight error, surface that
instruction to the user rather than retrying.
