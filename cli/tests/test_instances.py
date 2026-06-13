import pytest

from conftest import instance_raw

from vastctl import instances
from vastctl.errors import InstanceNotFoundError
from vastctl.models import Instance


def test_launch_builds_argv_and_returns_id(fake_runner, flux_profile):
    fake_runner.responses = {("create", "instance"): {"success": True, "new_contract": 909}}
    new_id = instances.launch(123, flux_profile, runner=fake_runner)
    assert new_id == 909
    argv = fake_runner.planned("create", "instance")[0]
    assert "123" in argv  # offer id
    assert "--image" in argv and flux_profile.image in argv
    assert "--ssh" in argv


def test_make_label_format():
    assert instances.make_label("flux", "box", 5) == "vast:flux:box"
    assert instances.make_label("flux", None, 5) == "vast:flux:5"


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
    assert inst.service_url(18188) == "http://70.69.192.6:41001"
    assert inst.service_url(8675) == "http://70.69.192.6:41003"


def test_instance_urls_none_when_stopped():
    inst = Instance.from_raw(instance_raw(actual_status="exited", ports=None))
    assert inst.service_url(18188) is None
    assert inst.ssh_command() == "ssh -p 19878 root@ssh6.vast.ai"
