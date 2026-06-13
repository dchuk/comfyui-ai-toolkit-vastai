"""Download files off an instance over SSH with rsync.

Backs up AI-Toolkit outputs/datasets before tearing a GPU box down. The argv
construction is a pure function so it can be unit-tested without touching the
network; the actual subprocess call is a thin wrapper.
"""

from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .errors import VastError
from .models import (
    AI_TOOLKIT_DATASETS_DIR,
    AI_TOOLKIT_DB_PATHS,
    AI_TOOLKIT_OUTPUT_DIR,
    Instance,
)

#: SSH options that mirror what the rest of the CLI uses for throwaway hosts:
#: don't prompt on / pollute known_hosts (instance host keys are ephemeral).
_SSH_OPTS = ("-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null")


@dataclass(frozen=True)
class Target:
    """One thing to back up: a remote path and the local subdir it lands in."""

    name: str
    remote: str
    is_dir: bool = True


def targets_for(outputs: bool, datasets: bool, db: bool) -> list[Target]:
    """Resolve the selected backup targets to concrete remote paths."""
    out: list[Target] = []
    if outputs:
        out.append(Target("output", AI_TOOLKIT_OUTPUT_DIR))
    if datasets:
        out.append(Target("datasets", AI_TOOLKIT_DATASETS_DIR))
    if db:
        for p in AI_TOOLKIT_DB_PATHS:
            # a basename with a file extension (aitk_db.db) is a file; jobs/ is a dir
            is_dir = "." not in Path(p).name
            out.append(Target(Path(p).name, p, is_dir=is_dir))
    return out


def ssh_endpoint(inst: Instance) -> tuple[str, str]:
    """(host, ssh_port) for direct key-based SSH into the instance.

    Uses the public IP + the host port mapped to container port 22 (entrypoint
    launch mode exposes our own sshd there). Raises if not yet available.
    """
    host = inst.public_ip
    port = inst.host_port(22)
    if not host or not port:
        raise VastError(
            f"instance {inst.id} has no SSH port mapped yet "
            "(still booting?). Try again once `vast ls` shows it running."
        )
    return host, port


def _write_backup_gitignore(dest_root: Path) -> None:
    """Make the backup dir self-ignoring so downloads are never committed.

    Drops a `.gitignore` of `*` into dest_root, so the whole tree is ignored by
    git no matter where --dest points (in addition to the repo's own ignore of
    the default ./vast-backups). Idempotent.
    """
    dest_root.mkdir(parents=True, exist_ok=True)
    gitignore = dest_root / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(
            "# vast CLI backups — downloaded datasets/LoRAs, never commit these.\n*\n"
        )


def build_rsync_argv(host: str, port: str, key: str, target: Target, local_dest: Path) -> list[str]:
    """Build the rsync argv for one target.

    Directory targets use a trailing slash so their *contents* land inside
    ``local_dest/<name>/``; single files copy into ``local_dest/``.
    """
    ssh = " ".join(["ssh", "-p", str(port), "-i", str(key), *_SSH_OPTS])
    if target.is_dir:
        src = f"root@{host}:{target.remote}/"
        dst = f"{local_dest}/{target.name}/"
    else:
        src = f"root@{host}:{target.remote}"
        dst = f"{local_dest}/"
    # --progress (not --info=progress2): portable to the old BSD rsync 2.6.9 that
    # ships on macOS as well as rsync 3.x.
    return ["rsync", "-az", "--partial", "--progress", "-e", ssh, src, dst]


def pull(
    inst: Instance,
    key: str,
    targets: list[Target],
    dest_root: Path,
    *,
    dry_run: bool = False,
    runner=subprocess.run,
) -> list[list[str]]:
    """rsync each target down into ``dest_root/<instance>/<name>``.

    Returns the list of rsync argvs that were run (or would run, on dry_run).
    """
    host, port = ssh_endpoint(inst)
    label = (inst.label or "").split(":")[-1] or str(inst.id)
    local_dest = dest_root / label
    planned: list[list[str]] = []
    if not dry_run:
        _write_backup_gitignore(dest_root)
    for target in targets:
        argv = build_rsync_argv(host, port, key, target, local_dest)
        planned.append(argv)
        if dry_run:
            continue
        if target.is_dir:
            (local_dest / target.name).mkdir(parents=True, exist_ok=True)
        else:
            local_dest.mkdir(parents=True, exist_ok=True)
        result = runner(argv)
        if getattr(result, "returncode", 0) != 0:
            raise VastError(f"rsync failed for {target.name}: {shlex.join(argv)}")
    return planned
