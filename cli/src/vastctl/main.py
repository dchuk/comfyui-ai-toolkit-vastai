"""`vast` — automate launching the ComfyUI + AI-Toolkit template on VastAI."""

from __future__ import annotations

import shlex
import sys
import uuid
from pathlib import Path
from typing import Optional

import typer

from . import instances, offers, profiles, readiness, template, vastai
from .errors import ReadinessTimeout, VastError
from .models import DEFAULT_TEMPLATE_NAME, Profile

app = typer.Typer(
    add_completion=False,
    help="Automate launching the ComfyUI + AI-Toolkit template on VastAI.",
    no_args_is_help=True,
)
template_app = typer.Typer(help="Manage the VastAI template independently of launches.")
app.add_typer(template_app, name="template")


def _fail(msg: str) -> "typer.Exit":
    typer.secho(f"error: {msg}", fg=typer.colors.RED, err=True)
    return typer.Exit(code=1)


def _parse_env(pairs: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in pairs:
        if "=" not in item:
            raise typer.BadParameter(f"--env expects KEY=VALUE, got '{item}'")
        key, value = item.split("=", 1)
        out[key.strip()] = value
    return out


#: SSH public keys to auto-authorize, in preference order, when --ssh-key is unset.
_DEFAULT_PUBKEYS = ("id_ed25519.pub", "id_rsa.pub")


def _resolve_ssh_pubkey(ssh_key: Optional[str]) -> Optional[str]:
    """Read the SSH public key to authorize on the instance.

    With an explicit path, that file is used (error if unreadable). Otherwise the
    first existing ~/.ssh/<default>.pub is used, or None if none exist.
    """
    if ssh_key:
        path = Path(ssh_key).expanduser()
        if not path.is_file():
            raise typer.BadParameter(f"--ssh-key file not found: {path}")
        return path.read_text().strip()
    ssh_dir = Path.home() / ".ssh"
    for name in _DEFAULT_PUBKEYS:
        path = ssh_dir / name
        if path.is_file():
            return path.read_text().strip()
    return None


def _print_urls(inst) -> None:
    typer.secho(f"\ninstance {inst.id} ({inst.gpu_name}) — {inst.status}", bold=True)
    for svc in inst.service_urls():
        typer.echo(f"  {svc.name:<16} {svc.url or '(pending)'}")
    ssh = inst.ssh_command()
    if ssh:
        typer.echo(f"  {'SSH':<16} {ssh}")


# --------------------------------------------------------------------------- up


@app.command()
def up(
    profile: str = typer.Argument(..., help="Use-case profile (sdxl/flux/train)."),
    name: Optional[str] = typer.Option(None, help="Friendly name for the instance label."),
    max_dph: Optional[float] = typer.Option(None, "--max-dph", help="Max price/hr ceiling."),
    gpu_ram: Optional[int] = typer.Option(None, "--gpu-ram", help="Override min GPU RAM (GB)."),
    gpu_name: Optional[str] = typer.Option(None, "--gpu-name", help="Require a GPU model."),
    disk: Optional[int] = typer.Option(None, help="Override disk (GB)."),
    image: Optional[str] = typer.Option(None, help="Override Docker image."),
    env: list[str] = typer.Option([], "--env", help="Extra env: KEY=VALUE (repeatable)."),
    pin_comfyui: Optional[str] = typer.Option(None, "--pin-comfyui", help="COMFYUI_VERSION."),
    pin_ai_toolkit: Optional[str] = typer.Option(None, "--pin-ai-toolkit", help="AI_TOOLKIT_VERSION."),
    template_name: str = typer.Option(DEFAULT_TEMPLATE_NAME, "--template-name", help="Template name."),
    profiles_path: Optional[str] = typer.Option(None, "--profiles-path", help="Custom profiles.toml."),
    ssh_key: Optional[str] = typer.Option(None, "--ssh-key", help="Public key file to authorize for SSH (default: auto-detect ~/.ssh/*.pub)."),
    no_ssh_key: bool = typer.Option(False, "--no-ssh-key", help="Don't authorize any SSH key."),
    fastest: bool = typer.Option(False, "--fastest", help="Pick the highest-bandwidth offer (within budget) instead of the cheapest."),
    force: bool = typer.Option(False, "--force", help="Ignore the price ceiling."),
    no_wait: bool = typer.Option(False, "--no-wait", help="Don't wait for readiness."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print commands, mutate nothing."),
) -> None:
    """Ensure the template, pick the cheapest matching GPU, launch, and print URLs."""
    runner = vastai.DryRunner() if dry_run else vastai.run
    try:
        if not dry_run:
            vastai.preflight()
        env_overrides = _parse_env(env)
        if not no_ssh_key and "SSH_PUBLIC_KEY" not in env_overrides:
            pubkey = _resolve_ssh_pubkey(ssh_key)
            if pubkey:
                env_overrides["SSH_PUBLIC_KEY"] = pubkey
        overrides = profiles.Overrides(
            image=image,
            disk=disk,
            max_dph=max_dph,
            gpu_ram=gpu_ram,
            gpu_name=gpu_name,
            env=env_overrides,
            pin_comfyui=pin_comfyui,
            pin_ai_toolkit=pin_ai_toolkit,
        )
        prof = profiles.resolve(profile, path=profiles_path, overrides=overrides)

        template.ensure(prof, template_name, runner=runner)

        found = offers.search(prof, runner=runner)
        offer = offers.pick(found, max_dph=None if force else prof.max_dph, fastest=fastest)
        typer.echo(
            f"selected offer {offer.id}: {offer.gpu_name} {offer.gpu_ram_gb}GB "
            f"@ ${offer.dph:.3f}/hr ({offer.inet_down:.0f} Mbps down, "
            f"reliability {offer.reliability:.3f})"
        )

        inst_name = name or f"{profile}-{uuid.uuid4().hex[:6]}"
        label = instances.make_label(profile, inst_name)
        inst_id = instances.launch(offer.id, prof, label, runner=runner)
    except VastError as e:
        raise _fail(str(e))

    if dry_run:
        typer.secho("\n[dry-run] would run:", bold=True)
        for argv in runner.planned:
            typer.echo("  vastai " + shlex.join(argv))
        return

    typer.secho(f"launched instance {inst_id}", fg=typer.colors.GREEN)
    if no_wait:
        typer.echo("not waiting for readiness (--no-wait). Check: vast ls")
        return

    typer.echo("waiting for ComfyUI to become reachable (this can take a few minutes)...")
    try:
        inst = readiness.wait(inst_id)
        _print_urls(inst)
    except ReadinessTimeout as e:
        typer.secho(str(e), fg=typer.colors.YELLOW, err=True)
        typer.echo(f"launched but not yet confirmed ready. Tail logs: vast logs {inst_id} -f")


# --------------------------------------------------------------------------- ls


@app.command()
def ls(all_: bool = typer.Option(False, "--all", help="Include non-CLI instances.")) -> None:
    """List instances (CLI-managed by default)."""
    try:
        items = instances.list_all() if all_ else instances.list_managed()
    except VastError as e:
        raise _fail(str(e))
    if not items:
        typer.echo("no instances." + ("" if all_ else " (use --all to see everything)"))
        return
    typer.echo(f"{'ID':<10} {'LABEL':<22} {'GPU':<14} {'STATUS':<10} {'$/HR':>7}  COMFYUI")
    for i in items:
        url = i.service_url(18188) or "-"
        typer.echo(
            f"{i.id:<10} {(i.label or '-'):<22} {i.gpu_name:<14} "
            f"{i.status:<10} {i.dph:>7.3f}  {url}"
        )


# ------------------------------------------------------------------ lifecycle


@app.command()
def down(
    ref: str = typer.Argument(..., help="Instance id or label name."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation."),
) -> None:
    """Destroy an instance (irreversible)."""
    try:
        inst = instances.resolve(ref)
        if not yes:
            typer.confirm(
                f"destroy instance {inst.id} ({inst.gpu_name}, {inst.status})?", abort=True
            )
        instances.destroy(inst.id)
    except VastError as e:
        raise _fail(str(e))
    typer.secho(f"destroyed {inst.id}", fg=typer.colors.GREEN)


@app.command()
def stop(ref: str = typer.Argument(..., help="Instance id or label name.")) -> None:
    """Stop an instance (pauses billing for compute)."""
    _simple(ref, instances.stop, "stopped")


@app.command()
def start(ref: str = typer.Argument(..., help="Instance id or label name.")) -> None:
    """Start a stopped instance."""
    _simple(ref, instances.start, "started")


def _simple(ref: str, action, verb: str) -> None:
    try:
        inst = instances.resolve(ref)
        action(inst.id)
    except VastError as e:
        raise _fail(str(e))
    typer.secho(f"{verb} {inst.id}", fg=typer.colors.GREEN)


@app.command()
def logs(ref: str = typer.Argument(..., help="Instance id or label name.")) -> None:
    """Print instance logs."""
    try:
        inst = instances.resolve(ref)
        typer.echo(instances.logs(inst.id))
    except VastError as e:
        raise _fail(str(e))


@app.command()
def ssh(ref: str = typer.Argument(..., help="Instance id or label name.")) -> None:
    """Print the SSH command for an instance."""
    try:
        inst = instances.resolve(ref)
        typer.echo(instances.ssh_url(inst.id))
    except VastError as e:
        raise _fail(str(e))


# --------------------------------------------------------------- template subapp


@template_app.command("sync")
def template_sync(
    profile: str = typer.Argument("sdxl", help="Profile whose env/disk to apply."),
    template_name: str = typer.Option(DEFAULT_TEMPLATE_NAME, "--template-name"),
    profiles_path: Optional[str] = typer.Option(None, "--profiles-path"),
) -> None:
    """Create or update the template without launching anything."""
    try:
        prof = profiles.resolve(profile, path=profiles_path)
        hash_id = template.ensure(prof, template_name)
    except VastError as e:
        raise _fail(str(e))
    typer.secho(f"template '{template_name}' synced (hash {hash_id})", fg=typer.colors.GREEN)


@template_app.command("show")
def template_show(
    template_name: str = typer.Option(DEFAULT_TEMPLATE_NAME, "--template-name"),
) -> None:
    """Show the current template, if any."""
    try:
        found = template.find(template_name)
    except VastError as e:
        raise _fail(str(e))
    if not found:
        typer.echo(f"no template named '{template_name}'")
        return
    typer.echo(f"name:   {found.get('name')}")
    typer.echo(f"hash:   {found.get('hash_id')}")
    typer.echo(f"image:  {found.get('image')}")
    typer.echo(f"disk:   {found.get('disk_space')}")


def main() -> None:
    app()


if __name__ == "__main__":
    sys.exit(app())
