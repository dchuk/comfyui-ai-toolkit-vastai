from pathlib import Path

import pytest

from conftest import instance_raw

from vastctl import transfer
from vastctl.errors import VastError
from vastctl.models import Instance


def test_targets_for_default_is_outputs_and_datasets():
    ts = transfer.targets_for(outputs=True, datasets=True, db=False)
    assert [t.name for t in ts] == ["output", "datasets"]
    assert all(t.is_dir for t in ts)
    assert ts[0].remote == "/workspace/ai-toolkit/output"


def test_targets_for_db_classifies_file_vs_dir():
    ts = transfer.targets_for(outputs=False, datasets=False, db=True)
    by_name = {t.name: t for t in ts}
    assert by_name["aitk_db.db"].is_dir is False  # a file
    assert by_name["jobs"].is_dir is True          # a directory


def test_targets_for_none_selected():
    assert transfer.targets_for(outputs=False, datasets=False, db=False) == []


def test_build_rsync_argv_dir_uses_trailing_slash():
    target = transfer.Target("output", "/workspace/ai-toolkit/output")
    argv = transfer.build_rsync_argv("1.2.3.4", "41000", "/home/u/.ssh/id_ed25519", target, Path("/bk/box"))
    # the -e value is the ssh command with port + key
    e_idx = argv.index("-e")
    assert argv[e_idx + 1] == "ssh -p 41000 -i /home/u/.ssh/id_ed25519 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
    # dir target: trailing slash on both src and dest so contents land in <dest>/output/
    assert argv[-2] == "root@1.2.3.4:/workspace/ai-toolkit/output/"
    assert argv[-1] == "/bk/box/output/"


def test_build_rsync_argv_file_has_no_trailing_slash():
    target = transfer.Target("aitk_db.db", "/workspace/ai-toolkit/aitk_db.db", is_dir=False)
    argv = transfer.build_rsync_argv("1.2.3.4", "41000", "/k", target, Path("/bk/box"))
    assert argv[-2] == "root@1.2.3.4:/workspace/ai-toolkit/aitk_db.db"
    assert argv[-1] == "/bk/box/"


def test_ssh_endpoint_uses_public_ip_and_port_22():
    inst = Instance.from_raw(instance_raw())
    host, port = transfer.ssh_endpoint(inst)
    assert host == "70.69.192.6"
    assert port == "41000"  # mapped to container 22


def test_ssh_endpoint_raises_when_no_port_mapped():
    inst = Instance.from_raw(instance_raw(ports={}))
    with pytest.raises(VastError, match="no SSH port"):
        transfer.ssh_endpoint(inst)


def test_pull_dry_run_plans_without_running(tmp_path):
    inst = Instance.from_raw(instance_raw(label="vast:train:mybox"))
    calls = []

    def boom(argv):  # must never be called in dry-run
        calls.append(argv)
        raise AssertionError("subprocess should not run in dry-run")

    planned = transfer.pull(
        inst, "/k",
        transfer.targets_for(outputs=True, datasets=True, db=False),
        tmp_path, dry_run=True, runner=boom,
    )
    assert calls == []
    assert len(planned) == 2
    # destination folds in the label segment
    assert planned[0][-1] == f"{tmp_path}/mybox/output/"
    assert planned[1][-1] == f"{tmp_path}/mybox/datasets/"


def test_pull_runs_rsync_and_creates_dest(tmp_path):
    inst = Instance.from_raw(instance_raw(label="vast:train:mybox"))
    ran = []

    class Ok:
        returncode = 0

    def runner(argv):
        ran.append(argv)
        return Ok()

    transfer.pull(
        inst, "/k",
        transfer.targets_for(outputs=True, datasets=False, db=False),
        tmp_path, runner=runner,
    )
    assert len(ran) == 1
    assert (tmp_path / "mybox" / "output").is_dir()
    # the backup dir self-ignores so downloads are never committed
    assert (tmp_path / ".gitignore").read_text().strip().endswith("*")


def test_pull_dry_run_writes_no_gitignore(tmp_path):
    inst = Instance.from_raw(instance_raw(label="vast:train:mybox"))
    transfer.pull(
        inst, "/k",
        transfer.targets_for(outputs=True, datasets=True, db=False),
        tmp_path, dry_run=True, runner=lambda argv: None,
    )
    assert not (tmp_path / ".gitignore").exists()


def test_pull_raises_on_rsync_failure(tmp_path):
    inst = Instance.from_raw(instance_raw(label="vast:train:mybox"))

    class Fail:
        returncode = 1

    with pytest.raises(VastError, match="rsync failed"):
        transfer.pull(
            inst, "/k",
            transfer.targets_for(outputs=True, datasets=False, db=False),
            tmp_path, runner=lambda argv: Fail(),
        )
