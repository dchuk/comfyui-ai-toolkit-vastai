"""Load and resolve use-case profiles from profiles.toml."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .errors import ProfileError
from .models import Profile

#: Bundled defaults shipped inside the package; override with --profiles-path.
DEFAULT_PROFILES_PATH = Path(__file__).resolve().parent / "profiles.toml"


@dataclass
class Overrides:
    """CLI flags that override resolved profile values."""

    image: str | None = None
    disk: int | None = None
    max_dph: float | None = None
    gpu_ram: int | None = None
    gpu_name: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    pin_comfyui: str | None = None
    pin_ai_toolkit: str | None = None


def load_config(path: str | Path | None = None) -> dict:
    p = Path(path) if path else DEFAULT_PROFILES_PATH
    if not p.exists():
        raise ProfileError(f"profiles file not found: {p}")
    try:
        with p.open("rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ProfileError(f"profiles file is not valid TOML ({p}): {e}") from e


def available(path: str | Path | None = None) -> list[str]:
    return sorted(load_config(path).get("profiles", {}))


def resolve(
    name: str,
    *,
    path: str | Path | None = None,
    overrides: Overrides | None = None,
) -> Profile:
    """Merge [defaults] with the named profile, then apply CLI overrides."""
    cfg = load_config(path)
    defaults = cfg.get("defaults", {})
    profiles = cfg.get("profiles", {})
    if name not in profiles:
        raise ProfileError(
            f"unknown profile '{name}'. available: {', '.join(sorted(profiles)) or '(none)'}"
        )
    p = profiles[name]
    if "search" not in p:
        raise ProfileError(f"profile '{name}' is missing a 'search' query")

    env = {**defaults.get("env", {}), **p.get("env", {})}
    prof = Profile(
        name=name,
        image=p.get("image", defaults.get("image", "")),
        disk=int(p.get("disk", defaults.get("disk", 40))),
        search=str(p["search"]),
        env={str(k): str(v) for k, v in env.items()},
        max_dph=_as_float(p.get("max_dph", defaults.get("max_dph"))),
    )
    if not prof.image:
        raise ProfileError(f"profile '{name}' has no image (set one in [defaults] or the profile)")
    if overrides:
        _apply(prof, overrides)
    return prof


def _apply(prof: Profile, o: Overrides) -> None:
    if o.image:
        prof.image = o.image
    if o.disk is not None:
        prof.disk = o.disk
    if o.max_dph is not None:
        prof.max_dph = o.max_dph
    # GPU constraints append to the raw search query (vastai ANDs the tokens).
    if o.gpu_ram is not None:
        prof.search = f"{prof.search} gpu_ram>={o.gpu_ram}"
    if o.gpu_name:
        prof.search = f"{prof.search} gpu_name=={o.gpu_name}"
    # Version pins map onto the template's env contract.
    if o.pin_comfyui:
        prof.env["COMFYUI_VERSION"] = o.pin_comfyui
    if o.pin_ai_toolkit:
        prof.env["AI_TOOLKIT_VERSION"] = o.pin_ai_toolkit
    # Arbitrary -e overrides win last.
    for k, v in o.env.items():
        prof.env[k] = v


def _as_float(v) -> float | None:
    return None if v is None else float(v)
