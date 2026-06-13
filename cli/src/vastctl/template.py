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
    runner = runner or vastai.run
    results = runner(["search", "templates", f'name == "{name}"']) or []
    for tpl in results:
        if tpl.get("name") == name:
            return tpl
    return None


def ensure(profile: Profile, name: str, runner=None) -> str:
    """Ensure a template named `name` exists and matches the profile.

    Returns the template hash_id. Creates when absent, updates only on drift.
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
        res = runner(
            ["create", "template", "--name", name, *config_args, "--desc", DEFAULT_DESC]
        )
        return _hash_id(res)

    if _drifted(existing, profile, env):
        runner(["update", "template", existing["hash_id"], *config_args])
    return existing["hash_id"]


def _drifted(existing: dict, profile: Profile, env: str) -> bool:
    if existing.get("image") not in (profile.image, profile.image.split(":")[0]):
        return True
    if int(existing.get("disk_space", 0) or 0) != profile.disk:
        return True
    # `env`/`recommended_disk_space` shapes vary across vastai versions; compare
    # the env string when present, otherwise fall back to updating to be safe.
    existing_env = existing.get("env") or existing.get("extra_env")
    if isinstance(existing_env, str):
        return existing_env.strip() != env.strip()
    return True


def _hash_id(res) -> str:
    if isinstance(res, dict):
        return str(res.get("hash_id") or res.get("id") or "")
    return ""


def _quote(value: str) -> str:
    return f'"{value}"' if " " in value else value
