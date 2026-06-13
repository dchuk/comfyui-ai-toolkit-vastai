import pytest

from conftest import instance_raw

from vastctl import readiness
from vastctl.errors import ReadinessTimeout


def fake_clock(values):
    it = iter(values)
    last = [0.0]

    def _():
        try:
            last[0] = float(next(it))
        except StopIteration:
            pass
        return last[0]

    return _


def test_wait_returns_when_running_and_probe_ok(fake_runner):
    fake_runner.responses = {("show", "instances"): [instance_raw(id=555)]}
    inst = readiness.wait(
        555,
        runner=fake_runner,
        prober=lambda url: True,
        sleep=lambda s: None,
        clock=fake_clock([0]),
    )
    assert inst.id == 555


def test_wait_times_out_when_never_ready(fake_runner):
    # status never reaches running -> must time out, not hang
    fake_runner.responses = {
        ("show", "instances"): [instance_raw(id=555, actual_status="loading", ports=None)]
    }
    with pytest.raises(ReadinessTimeout) as exc:
        readiness.wait(
            555,
            runner=fake_runner,
            timeout=10,
            prober=lambda url: True,
            sleep=lambda s: None,
            clock=fake_clock([0, 5, 1000]),
        )
    assert exc.value.instance is not None


def test_wait_times_out_when_probe_never_succeeds(fake_runner):
    fake_runner.responses = {("show", "instances"): [instance_raw(id=555)]}
    with pytest.raises(ReadinessTimeout):
        readiness.wait(
            555,
            runner=fake_runner,
            timeout=10,
            prober=lambda url: False,  # running but service never answers
            sleep=lambda s: None,
            clock=fake_clock([0, 5, 1000]),
        )


def test_safe_probe_swallows_exceptions():
    def boom(url):
        raise RuntimeError("connection refused")

    assert readiness._safe_probe(boom, "http://x") is False
