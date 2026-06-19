"""Best-effort readiness: wait for the instance to run AND for ComfyUI to answer.

`actual_status == running` only means the container started; ComfyUI may still
be installing/auto-updating. The real signal is an HTTP response on ComfyUI's
Caddy-proxied port (18189). Caddy fronts it with basic_auth, so an
unauthenticated probe gets 401 (still < 500 → "up": the proxy + upstream are
live; a down upstream returns 502). Timeouts degrade gracefully — we never hang
forever, and the caller reports a "launched but not yet confirmed" message with
a `vast logs` hint.
"""

from __future__ import annotations

import time

from . import instances
from .errors import ReadinessTimeout
from .models import READINESS_PORT_INTERNAL, Instance


def wait(
    instance_id: int,
    *,
    runner=None,
    timeout: float = 900.0,
    interval: float = 10.0,
    prober=None,
    sleep=time.sleep,
    clock=time.monotonic,
) -> Instance:
    """Poll until ComfyUI responds, or raise ReadinessTimeout after `timeout`s."""
    prober = prober or _http_probe
    deadline = clock() + timeout
    last: Instance | None = None

    while True:
        last = instances.get(instance_id, runner)
        if last and last.status == "running":
            url = last.service_url(READINESS_PORT_INTERNAL)
            if url and _safe_probe(prober, url):
                return last
        if clock() >= deadline:
            raise ReadinessTimeout(
                f"instance {instance_id} not confirmed ready after {int(timeout)}s "
                f"(last status: {last.status if last else 'unknown'})",
                instance=last,
            )
        sleep(interval)


def _safe_probe(prober, url: str) -> bool:
    try:
        return bool(prober(url))
    except Exception:
        return False


def _http_probe(url: str) -> bool:
    import httpx

    resp = httpx.get(url, timeout=5.0, follow_redirects=True)
    # Any non-server-error response means the proxy + service are up.
    return resp.status_code < 500
