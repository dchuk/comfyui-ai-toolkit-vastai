"""Instance lifecycle: launch, look up, label, and tear down."""

from __future__ import annotations

from . import template, vastai
from .errors import InstanceNotFoundError
from .models import Instance, Profile

#: Prefix on labels of CLI-managed instances, so `vast ls` can filter to ours.
LABEL_PREFIX = "vast"


def launch(offer_id: int, profile: Profile, runner=None) -> int:
    """Create an instance on a specific offer with the template's image/env."""
    runner = runner or vastai.run
    env = template.build_env(profile)
    res = runner(
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
            "--ssh",
            "--direct",
        ]
    )
    return _new_instance_id(res)


def label(instance_id: int, text: str, runner=None) -> None:
    runner = runner or vastai.run
    runner(["label", "instance", str(instance_id), text])


def make_label(profile_name: str, name: str | None, instance_id: int) -> str:
    return f"{LABEL_PREFIX}:{profile_name}:{name or instance_id}"


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
    (runner or vastai.run)(["destroy", "instance", str(instance_id)])


def stop(instance_id: int, runner=None) -> None:
    (runner or vastai.run)(["stop", "instance", str(instance_id)])


def start(instance_id: int, runner=None) -> None:
    (runner or vastai.run)(["start", "instance", str(instance_id)])


def logs(instance_id: int, runner=None) -> str:
    """Return raw log text (not JSON)."""
    return (runner or vastai.run)(["logs", str(instance_id)], raw=False)


def ssh_url(instance_id: int, runner=None) -> str:
    return (runner or vastai.run)(["ssh-url", str(instance_id)], raw=False).strip()


def _new_instance_id(res) -> int:
    if isinstance(res, dict):
        for key in ("new_contract", "id", "instance_id"):
            if res.get(key) is not None:
                return int(res[key])
    raise InstanceNotFoundError(f"could not read new instance id from vastai response: {res!r}")
