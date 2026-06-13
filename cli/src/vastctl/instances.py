"""Instance lifecycle: launch, look up, label, and tear down."""

from __future__ import annotations

import time

from . import template, vastai
from .errors import InstanceNotFoundError
from .models import Instance, Profile

#: Prefix on labels of CLI-managed instances, so `vast ls` can filter to ours.
LABEL_PREFIX = "vast"


def launch(offer_id: int, profile: Profile, label: str, runner=None, sleep=time.sleep) -> int:
    """Create an instance on a specific offer with the template's image/env.

    The label is set at creation time (`--label`) so we can resolve the new
    instance id by querying `show instances` — `create instance` prints a
    non-JSON confirmation, so its stdout is not parsed.
    """
    runner = runner or vastai.run
    env = template.build_env(profile)
    # Snapshot existing ids first so we can identify the genuinely new instance
    # afterwards — resolving purely by label would match a stale same-labelled
    # instance from a previous launch.
    before = {i.id for i in list_all(runner)}
    # `--args` (must be last) selects args/entrypoint launch mode: VastAI runs the
    # image as-is so the base ENTRYPOINT starts supervisor + all services. Using
    # --ssh instead would launch an ssh-only container and the portal/ComfyUI/
    # AI-Toolkit services would never start.
    runner(
        [
            "create",
            "instance",
            str(offer_id),
            "--image",
            profile.image,
            "--disk",
            str(profile.disk),
            "--env",
            env,
            "--label",
            label,
            "--args",
        ],
        raw=False,
    )
    # Dry-run never actually creates the instance; don't poll for it.
    if isinstance(runner, vastai.DryRunner):
        return 0
    inst = _find_new(before, label, runner, sleep=sleep)
    if inst is None:
        raise InstanceNotFoundError(
            f"instance was launched but did not appear as new; check `vast ls --all`"
        )
    return inst.id


def _find_new(before: set[int], label: str, runner, attempts: int = 6, delay: float = 2.0, sleep=time.sleep):
    """Find the instance created by the launch — an id not present before it.

    Prefers a new instance carrying the expected label; falls back to any new
    instance. Robust against stale instances reusing the same label.
    """
    for i in range(attempts):
        new = [inst for inst in list_all(runner) if inst.id not in before]
        labeled = [inst for inst in new if inst.label == label]
        if labeled:
            return labeled[0]
        if new:
            return new[0]
        if i < attempts - 1:
            sleep(delay)
    return None


def make_label(profile_name: str, name: str) -> str:
    return f"{LABEL_PREFIX}:{profile_name}:{name}"


def list_all(runner=None) -> list[Instance]:
    runner = runner or vastai.run
    data = runner(["show", "instances"]) or []
    return [Instance.from_raw(d) for d in data]


def list_managed(runner=None) -> list[Instance]:
    return [i for i in list_all(runner) if (i.label or "").startswith(f"{LABEL_PREFIX}:")]


def get(instance_id: int, runner=None) -> Instance | None:
    for inst in list_all(runner):
        if inst.id == instance_id:
            return inst
    return None


def resolve(ref: str, runner=None) -> Instance:
    """Resolve a reference (numeric id, or the trailing name of a vast: label)."""
    instances = list_all(runner)
    if ref.isdigit():
        wanted = int(ref)
        for inst in instances:
            if inst.id == wanted:
                return inst
    # match by label name segment: vast:<profile>:<name>
    matches = [i for i in instances if (i.label or "").split(":")[-1] == ref]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        ids = ", ".join(str(m.id) for m in matches)
        raise InstanceNotFoundError(f"'{ref}' is ambiguous — matches instances: {ids}")
    raise InstanceNotFoundError(f"no instance matching '{ref}'")


def destroy(instance_id: int, runner=None) -> None:
    # -y: `vastai destroy` prompts for confirmation otherwise (we confirm in the
    # CLI layer). raw=False: it prints a non-JSON confirmation, don't parse it.
    (runner or vastai.run)(["destroy", "instance", str(instance_id), "-y"], raw=False)


def stop(instance_id: int, runner=None) -> None:
    (runner or vastai.run)(["stop", "instance", str(instance_id)], raw=False)


def start(instance_id: int, runner=None) -> None:
    (runner or vastai.run)(["start", "instance", str(instance_id)], raw=False)


def logs(instance_id: int, runner=None) -> str:
    """Return raw log text (not JSON)."""
    return (runner or vastai.run)(["logs", str(instance_id)], raw=False)


def ssh_url(instance_id: int, runner=None) -> str:
    return (runner or vastai.run)(["ssh-url", str(instance_id)], raw=False).strip()
