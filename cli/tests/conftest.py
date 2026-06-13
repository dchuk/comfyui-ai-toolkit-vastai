"""Shared test fixtures. No test touches the network — the vastai runner is faked."""

from __future__ import annotations

import pytest

from vastctl.models import Profile


class FakeRunner:
    """Stand-in for `vastai.run`. Returns scripted responses keyed by argv prefix.

    responses maps a tuple prefix -> a value or a callable(args) -> value.
    Records every call in `.calls` for assertions.
    """

    def __init__(self, responses: dict | None = None):
        self.responses = responses or {}
        self.calls: list[list[str]] = []

    def __call__(self, args, raw: bool = True, timeout: int = 120):
        args = list(args)
        self.calls.append(args)
        for prefix, value in self.responses.items():
            if tuple(args[: len(prefix)]) == prefix:
                return value(args) if callable(value) else value
        return None

    def planned(self, *prefix) -> list[list[str]]:
        return [c for c in self.calls if tuple(c[: len(prefix)]) == prefix]


@pytest.fixture
def fake_runner():
    return FakeRunner()


@pytest.fixture
def flux_profile() -> Profile:
    return Profile(
        name="flux",
        image="dchuk/comfyui-ai-toolkit:latest",
        disk=60,
        search="gpu_ram>=24 num_gpus=1 rentable==True",
        env={"AUTO_UPDATE": "true"},
        max_dph=0.60,
    )


#: A realistic running-instance ports map (Docker-style). NOTE: confirmed shape
#: against a stopped instance (ports=null); the running shape below should be
#: re-validated against a live instance the first time one is launched.
RUNNING_PORTS = {
    "22/tcp": [{"HostIp": "0.0.0.0", "HostPort": "41000"}],
    "1111/tcp": [{"HostIp": "0.0.0.0", "HostPort": "41004"}],
    "18188/tcp": [{"HostIp": "0.0.0.0", "HostPort": "41001"}],
    "18288/tcp": [{"HostIp": "0.0.0.0", "HostPort": "41002"}],
    "8675/tcp": [{"HostIp": "0.0.0.0", "HostPort": "41003"}],
}


def instance_raw(**overrides) -> dict:
    base = {
        "id": 555,
        "label": "vast:flux:my-box",
        "actual_status": "running",
        "gpu_name": "RTX 4090",
        "dph_total": 0.42,
        "public_ipaddr": "70.69.192.6",
        "ssh_host": "ssh6.vast.ai",
        "ssh_port": 19878,
        "ports": RUNNING_PORTS,
    }
    base.update(overrides)
    return base


def offer_raw(
    id_: int,
    dph: float,
    reliability: float = 0.99,
    gpu_ram_mb: int = 24576,
    inet_down: float = 1000.0,
) -> dict:
    return {
        "id": id_,
        "dph_total": dph,
        "gpu_name": "RTX 4090",
        "gpu_ram": gpu_ram_mb,
        "num_gpus": 1,
        "reliability2": reliability,
        "inet_down": inet_down,
    }
