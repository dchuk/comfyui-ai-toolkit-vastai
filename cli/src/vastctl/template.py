"""Idempotent VastAI template management: create once, update on drift.

The template encodes the image, disk, the fixed HTTP port mappings, and the
profile env. We never create duplicates — we match by exact name and update in
place. The same env string is reused when launching instances directly, so the
template and the instance stay in lockstep.
"""

from __future__ import annotations

from . import vastai
from .models import HTTP_PORTS, Profile

DEFAULT_DESC = "Combined ComfyUI + AI-Toolkit (managed by the vast CLI)"


def build_env(profile: Profile) -> str:
    """Build the `--env` string: HTTP port mappings + `-e KEY=VALUE` pairs.

    Values containing spaces are double-quoted so vastai parses them as one
    token (e.g. COMFYUI_ARGS).
    """
    parts = [f"-p {port}:{port}" for port in HTTP_PORTS]
    for key, value in profile.env.items():
        parts.append(f"-e {key}={_quote(value)}")
    return " ".join(parts)


def find(name: str, runner=None) -> dict | None:
    """Find the authenticated user's own template by exact name.

    `search templates` returns the public marketplace unless filtered by
    `creator_id`, so we scope the search to the current user. If duplicates of
    the same name exist, the most recently created one wins.
    """
    runner = runner or vastai.run
    uid = vastai.current_user_id(runner)
    results = runner(["search", "templates", f"creator_id={uid}"]) or []
    matches = [t for t in results if t.get("name") == name]
    if not matches:
        return None
    return max(matches, key=lambda t: t.get("created_at") or 0)


def ensure(profile: Profile, name: str, runner=None) -> str:
    """Ensure a template named `name` exists and matches the profile.

    Returns the template hash_id. Creates when absent, updates only on drift.
    `create`/`update template` print a non-JSON confirmation, so we run them
    without parsing and re-query to obtain the hash_id.
    """
    runner = runner or vastai.run
    env = build_env(profile)
    config_args = [
        "--image",
        profile.image,
        "--disk_space",
        str(profile.disk),
        "--ssh",
        "--direct",
        "--env",
        env,
    ]

    existing = find(name, runner)
    if existing is None:
        runner(
            ["create", "template", "--name", name, *config_args, "--desc", DEFAULT_DESC],
            raw=False,
        )
        created = find(name, runner)
        return str(created.get("hash_id", "")) if created else ""

    if _drifted(existing, profile, env):
        runner(["update", "template", existing["hash_id"], *config_args], raw=False)
    return str(existing["hash_id"])


def _drifted(existing: dict, profile: Profile, env: str) -> bool:
    if existing.get("image") != profile.image:
        return True
    # disk is stored as `recommended_disk_space` (float), not `disk_space`.
    disk = existing.get("recommended_disk_space")
    if disk is not None and int(disk) != profile.disk:
        return True
    existing_env = existing.get("env")
    if isinstance(existing_env, str):
        return existing_env.strip() != env.strip()
    # No comparable env on the stored template -> update to be safe.
    return True


def _quote(value: str) -> str:
    return f'"{value}"' if " " in value else value
