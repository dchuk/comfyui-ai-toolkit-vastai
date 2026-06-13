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


def test_build_env_has_ports_and_quoted_values():
    env = template.build_env(_profile())
    assert "-p 1111:1111" in env
    assert "-p 18188:18188" in env
    assert "-e AUTO_UPDATE=true" in env
    # value with spaces must be quoted as one token
    assert '-e COMFYUI_ARGS="--port 18188 --enable-cors-header"' in env


def test_ensure_creates_when_absent(fake_runner):
    fake_runner.responses = {
        ("search", "templates"): [],
        ("create", "template"): {"hash_id": "NEWHASH"},
    }
    hash_id = template.ensure(_profile(), NAME, runner=fake_runner)
    assert hash_id == "NEWHASH"
    created = fake_runner.planned("create", "template")
    assert created, "should have created a template"
    argv = created[0]
    assert "--name" in argv and NAME in argv
    assert "--ssh" in argv and "--direct" in argv


def test_ensure_updates_on_drift(fake_runner):
    fake_runner.responses = {
        ("search", "templates"): [
            {"name": NAME, "hash_id": "H1", "image": "old/image:tag", "disk_space": 60, "env": ""}
        ],
        ("update", "template"): {"hash_id": "H1"},
    }
    template.ensure(_profile(), NAME, runner=fake_runner)
    assert fake_runner.planned("update", "template"), "drift should trigger an update"
    assert not fake_runner.planned("create", "template")


def test_ensure_noop_when_identical(fake_runner):
    prof = _profile()
    env = template.build_env(prof)
    fake_runner.responses = {
        ("search", "templates"): [
            {"name": NAME, "hash_id": "H1", "image": prof.image, "disk_space": prof.disk, "env": env}
        ],
    }
    hash_id = template.ensure(prof, NAME, runner=fake_runner)
    assert hash_id == "H1"
    assert not fake_runner.planned("update", "template")
    assert not fake_runner.planned("create", "template")
