"""The single chokepoint over the `vastai` CLI.

Every module reaches VastAI through `run()` (or a runner injected for tests /
dry-run). Import this module and call ``vastai.run(...)`` rather than
``from .vastai import run`` so that patching ``vastctl.vastai.run`` works.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any, Sequence

from .errors import PreflightError, VastaiCLIError

BIN = "vastai"

#: vastai subcommand verbs that change state — intercepted by DryRunner.
MUTATING_VERBS = {
    "create",
    "update",
    "launch",
    "destroy",
    "delete",
    "start",
    "stop",
    "reboot",
    "recycle",
    "label",
}


def run(args: Sequence[str], raw: bool = True, timeout: int = 120) -> Any:
    """Run `vastai <args>`. Returns parsed JSON when raw, else raw stdout text.

    Raises PreflightError if the CLI is absent, VastaiCLIError on failure or
    unparseable output.
    """
    cmd = [BIN, *args]
    if raw and "--raw" not in args:
        cmd = [*cmd, "--raw"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as e:
        raise PreflightError(
            "vastai CLI not found on PATH. Install it with: pip install vastai"
        ) from e
    except subprocess.TimeoutExpired as e:
        raise VastaiCLIError(f"vastai {' '.join(args)} timed out after {timeout}s") from e

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise VastaiCLIError(
            f"vastai {' '.join(args)} failed (exit {proc.returncode}): {detail}"
        )

    if not raw:
        return proc.stdout

    out = proc.stdout.strip()
    if not out:
        return None
    # Some vastai subcommands (e.g. `search templates`) append a trailing line
    # like `null` after the JSON result. Decode the first JSON document and
    # ignore any trailing content rather than failing the whole call.
    try:
        value, _end = json.JSONDecoder().raw_decode(out)
        return value
    except json.JSONDecodeError as e:
        raise VastaiCLIError(
            f"vastai {' '.join(args)} returned non-JSON output: {out[:200]}"
        ) from e


def preflight(runner=None) -> None:
    """Verify the CLI is installed and authenticated.

    `vastai show user` requires a valid api-key, so it doubles as an auth check.
    """
    runner = runner or run
    try:
        runner(["show", "user"], raw=True)
    except PreflightError:
        raise
    except VastaiCLIError as e:
        raise PreflightError(
            "vastai CLI is not authenticated. Run: vastai set api-key YOUR_API_KEY"
        ) from e


class DryRunner:
    """A runner that executes read-only commands for real but records mutating
    ones without running them, returning plausible stand-in data so the flow
    proceeds. `planned` holds the argv lists that *would* have mutated state.
    """

    def __init__(self, real=None):
        self.real = real or run
        self.planned: list[list[str]] = []

    def __call__(self, args: Sequence[str], raw: bool = True, timeout: int = 120) -> Any:
        args = list(args)
        if args and args[0] in MUTATING_VERBS:
            self.planned.append(args)
            return self._fake(args)
        return self.real(args, raw=raw, timeout=timeout)

    @staticmethod
    def _fake(args: list[str]) -> Any:
        head = args[:2]
        if head in (["create", "template"], ["update", "template"]):
            return {"hash_id": "DRYRUN_TEMPLATE_HASH", "id": 0, "success": True}
        if head == ["create", "instance"]:
            return {"success": True, "new_contract": 0}
        return {"success": True}
