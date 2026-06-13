"""Tests for the vastai CLI wrapper's handling of v0.5.0 output quirks."""

import subprocess

import pytest

from vastctl import vastai
from vastctl.errors import PreflightError, VastaiCLIError


def _completed(stdout: str, returncode: int = 0):
    return subprocess.CompletedProcess(args=["vastai"], returncode=returncode, stdout=stdout, stderr="")


def test_run_raises_on_exit0_error_string(monkeypatch):
    # `vastai show user` exits 0 but prints an error to stdout — must be caught.
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: _completed("failed with error 400: owner: Extra inputs are not permitted")
    )
    with pytest.raises(VastaiCLIError) as exc:
        vastai.run(["show", "user"])
    assert "failed with error 400" in str(exc.value)


def test_run_ignores_trailing_null(monkeypatch):
    # `vastai search templates` appends a trailing `null` line after the JSON.
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _completed("[]\nnull\n"))
    assert vastai.run(["search", "templates", 'name == "x"']) == []


def test_run_parses_normal_json(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _completed('[{"id": 1}]'))
    assert vastai.run(["show", "instances"]) == [{"id": 1}]


def test_preflight_uses_show_instances_and_passes(monkeypatch):
    calls = []

    def fake_run(args, raw=True, timeout=120):
        calls.append(list(args))
        return []  # authenticated -> valid (empty) list

    vastai.preflight(runner=fake_run)
    assert calls == [["show", "instances"]]  # not "show user"


def test_preflight_reports_auth_error(monkeypatch):
    def fake_run(args, raw=True, timeout=120):
        raise VastaiCLIError("boom")

    with pytest.raises(PreflightError):
        vastai.preflight(runner=fake_run)
