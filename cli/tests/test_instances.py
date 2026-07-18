import pytest

from conftest import instance_raw

from vastctl import instances
from vastctl.errors import InstanceNotFoundError
from vastctl.models import Instance


def test_launch_labels_at_create_and_resolves_id(fake_runner, flux_profile):
    label = "vast:flux:box"
    # A stale instance already carries the same label; the new one must still be
    # picked via the before/after id diff, not the stale match.
    state = {"created": False}

    def show(_args):
        base = [instance_raw(id=100, label=label)]  # stale, pre-existing
        return base + [instance_raw(id=909, label=label)] if state["created"] else base

    def create(_args):
        state["created"] = True
        return ""

    fake_runner.responses = {("create", "instance"): create, ("show", "instances"): show}
    new_id = instances.launch(123, flux_profile, label, runner=fake_runner, sleep=lambda s: None)
    assert new_id == 909  # the new id, not the stale 100
    argv = fake_runner.planned("create", "instance")[0]
    assert "123" in argv  # offer id
    assert "--image" in argv and flux_profile.image in argv
    assert "--label" in argv and label in argv
    # entrypoint/args launch mode (not ssh-only) so services actually start
    assert "--ssh" not in argv
    assert argv[-1] == "--args"


def test_make_label_format():
    assert instances.make_label("flux", "box") == "vast:flux:box"


def test_resolve_by_id(fake_runner):
    fake_runner.responses = {("show", "instances"): [instance_raw(id=555)]}
    assert instances.resolve("555", runner=fake_runner).id == 555


def test_resolve_by_label_name(fake_runner):
    fake_runner.responses = {("show", "instances"): [instance_raw(label="vast:flux:my-box")]}
    assert instances.resolve("my-box", runner=fake_runner).label == "vast:flux:my-box"


def test_resolve_unknown_raises(fake_runner):
    fake_runner.responses = {("show", "instances"): []}
    with pytest.raises(InstanceNotFoundError):
        instances.resolve("ghost", runner=fake_runner)


def test_resolve_ambiguous_raises(fake_runner):
    fake_runner.responses = {
        ("show", "instances"): [
            instance_raw(id=1, label="vast:flux:dup"),
            instance_raw(id=2, label="vast:sdxl:dup"),
        ]
    }
    with pytest.raises(InstanceNotFoundError):
        instances.resolve("dup", runner=fake_runner)


def test_list_managed_filters(fake_runner):
    fake_runner.responses = {
        ("show", "instances"): [
            instance_raw(id=1, label="vast:flux:a"),
            instance_raw(id=2, label=None),
            instance_raw(id=3, label="something-else"),
        ]
    }
    managed = instances.list_managed(runner=fake_runner)
    assert [i.id for i in managed] == [1]


def test_instance_service_urls_from_running_ports():
    inst = Instance.from_raw(instance_raw())
    assert inst.service_url(18189) == "http://70.69.192.6:41001"
    assert inst.service_url(8676) == "http://70.69.192.6:41003"


def test_instance_urls_none_when_stopped():
    inst = Instance.from_raw(instance_raw(actual_status="exited", ports=None))
    assert inst.service_url(18189) is None
    assert inst.ssh_command() == "ssh -p 19878 root@ssh6.vast.ai"
