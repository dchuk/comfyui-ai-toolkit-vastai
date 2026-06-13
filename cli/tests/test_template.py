from vastctl import template
from vastctl.models import Profile

NAME = "ComfyUI + AI-Toolkit"


def _profile(**kw) -> Profile:
    base = dict(
        name="flux",
        image="dchuk/comfyui-ai-toolkit:latest",
        disk=60,
        search="gpu_ram>=24",
        env={"AUTO_UPDATE": "true", "COMFYUI_ARGS": "--port 18188 --enable-cors-header"},
        max_dph=0.6,
    )
    base.update(kw)
    return Profile(**base)


def _stored(prof, **overrides) -> dict:
    """A template as `search templates` would return it for this user."""
    base = {
        "name": NAME,
        "hash_id": "H1",
        "image": prof.image,
        "recommended_disk_space": float(prof.disk),
        "env": template.build_env(prof),
        "created_at": 100.0,
    }
    base.update(overrides)
    return base


def test_build_env_has_ports_and_quoted_values():
    env = template.build_env(_profile())
    assert "-p 1111:1111" in env
    assert "-p 18188:18188" in env
    assert "-e AUTO_UPDATE=true" in env
    # value with spaces must be quoted as one token
    assert '-e COMFYUI_ARGS="--port 18188 --enable-cors-header"' in env


def test_find_scopes_to_creator_id(fake_runner):
    prof = _profile()
    fake_runner.responses = {
        ("show", "user"): {"id": 42},
        ("search", "templates"): [_stored(prof)],
    }
    found = template.find(NAME, runner=fake_runner)
    assert found["hash_id"] == "H1"
    # the search must be filtered by this user's id, not the public marketplace
    assert fake_runner.planned("search", "templates")[0] == ["search", "templates", "creator_id=42"]


def test_ensure_creates_when_absent(fake_runner):
    prof = _profile()
    state = {"created": False}

    def templates(_args):
        return [_stored(prof, hash_id="NEWHASH")] if state["created"] else []

    def create(_args):
        state["created"] = True
        return ""

    fake_runner.responses = {
        ("show", "user"): {"id": 1},
        ("search", "templates"): templates,
        ("create", "template"): create,
    }
    hash_id = template.ensure(prof, NAME, runner=fake_runner)
    assert hash_id == "NEWHASH"
    argv = fake_runner.planned("create", "template")[0]
    assert "--name" in argv and NAME in argv
    # entrypoint mode: no ssh-only runtype forced on the template
    assert "--ssh" not in argv


def test_ensure_updates_on_drift(fake_runner):
    prof = _profile()
    fake_runner.responses = {
        ("show", "user"): {"id": 1},
        ("search", "templates"): [_stored(prof, image="old/image:tag")],
    }
    template.ensure(prof, NAME, runner=fake_runner)
    assert fake_runner.planned("update", "template")
    assert not fake_runner.planned("create", "template")


def test_ensure_noop_when_identical(fake_runner):
    prof = _profile()
    fake_runner.responses = {
        ("show", "user"): {"id": 1},
        ("search", "templates"): [_stored(prof)],
    }
    hash_id = template.ensure(prof, NAME, runner=fake_runner)
    assert hash_id == "H1"
    assert not fake_runner.planned("update", "template")
    assert not fake_runner.planned("create", "template")
