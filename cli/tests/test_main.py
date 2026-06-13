from typer.testing import CliRunner

from conftest import FakeRunner, instance_raw, offer_raw

from vastctl import main, vastai

cli = CliRunner()


def test_up_dry_run_plans_without_mutating(monkeypatch):
    fake = FakeRunner(
        {
            ("show", "user"): {"id": 7},
            ("search", "templates"): [],
            ("search", "offers"): [offer_raw(11, 0.20)],
        }
    )
    monkeypatch.setattr(vastai, "run", fake)

    result = cli.invoke(main.app, ["up", "flux", "--dry-run", "--max-dph", "1.0"])

    assert result.exit_code == 0, result.output
    # the plan is printed, with the label folded into `create instance`...
    assert "vastai create template" in result.output
    assert "vastai create instance" in result.output
    assert "--label" in result.output
    # ...but no mutating command ever reached the real runner
    assert all(c[0] in ("show", "search") for c in fake.calls)


def test_up_refuses_over_budget(monkeypatch):
    fake = FakeRunner(
        {
            ("show", "user"): {"id": 7},
            ("search", "templates"): [],
            ("search", "offers"): [offer_raw(11, 0.95)],
        }
    )
    monkeypatch.setattr(vastai, "run", fake)

    result = cli.invoke(main.app, ["up", "flux", "--dry-run", "--max-dph", "0.50"])

    assert result.exit_code == 1
    assert "0.95" in result.output


def test_ls_shows_managed(monkeypatch):
    fake = FakeRunner({("show", "instances"): [instance_raw(id=1, label="vast:flux:a")]})
    monkeypatch.setattr(vastai, "run", fake)

    result = cli.invoke(main.app, ["ls"])

    assert result.exit_code == 0, result.output
    assert "vast:flux:a" in result.output
    assert "http://70.69.192.6:41001" in result.output


def test_ls_empty(monkeypatch):
    fake = FakeRunner({("show", "instances"): []})
    monkeypatch.setattr(vastai, "run", fake)

    result = cli.invoke(main.app, ["ls"])

    assert result.exit_code == 0
    assert "no instances" in result.output
