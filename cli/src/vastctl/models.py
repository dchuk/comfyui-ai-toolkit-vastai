"""Dataclasses + the fixed runtime contract of the comfyui-ai-toolkit template.

Field names mirror the real `vastai ... --raw` JSON (verified against v0.5.0):
price is `dph_total`, GPU memory `gpu_ram` is in MB, instance address is
`public_ipaddr`, and the Docker-style `ports` map is null until the instance
is actually running.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# --- Template runtime contract (see comfyui-ai-toolkit/README.md + Dockerfile) ---

#: HTTP service ports that must be opened on the instance (22/ssh handled by --ssh).
#: 8080 is Jupyter's externally-exposed port (Caddy proxies it to internal 18080).
#: 18189 is ComfyUI's externally-exposed port: ComfyUI binds loopback (18188), so
#: Caddy reverse-proxies 18189 -> 18188 and wraps it in the portal's basic-auth.
HTTP_PORTS: tuple[int, ...] = (1111, 18189, 18288, 8675, 8080)

#: Service label -> externally-exposed container port, used to build access URLs.
SERVICE_PORTS: dict[str, int] = {
    "ComfyUI": 18189,
    "API Wrapper": 18288,
    "AI Toolkit": 8675,
    "Jupyter": 8080,
    "Instance Portal": 1111,
}

#: The service we HTTP-probe to decide an instance is genuinely ready. This is
#: ComfyUI's Caddy-proxied external port (18189); since Caddy fronts it with
#: basic_auth, an unauthenticated probe gets 401 — which still confirms the
#: Caddy + ComfyUI stack is up (a down upstream returns 502). See readiness.py.
READINESS_PORT_INTERNAL: int = 18189

#: Default VastAI template name (one per account; reused/updated, never duplicated).
DEFAULT_TEMPLATE_NAME = "ComfyUI + AI-Toolkit"

#: Remote AI-Toolkit paths the `pull` command backs up (on /workspace).
AI_TOOLKIT_OUTPUT_DIR = "/workspace/ai-toolkit/output"      # trained LoRAs (per-job dirs)
AI_TOOLKIT_DATASETS_DIR = "/workspace/ai-toolkit/datasets"  # uploaded training datasets
#: Job-history DB + run state (opt-in via --db); restores the AI-Toolkit UI's jobs.
AI_TOOLKIT_DB_PATHS = ("/workspace/ai-toolkit/aitk_db.db", "/workspace/ai-toolkit/jobs")


@dataclass
class Profile:
    """A resolved use-case profile (defaults merged with the chosen profile)."""

    name: str
    image: str
    disk: int
    search: str
    env: dict[str, str] = field(default_factory=dict)
    max_dph: float | None = None


@dataclass
class Offer:
    """A rentable GPU offer from `vastai search offers`."""

    id: int
    dph: float
    gpu_name: str
    gpu_ram_gb: float
    num_gpus: int
    reliability: float
    inet_down: float  # internet download speed, Mbps
    raw: dict

    @classmethod
    def from_raw(cls, d: dict) -> "Offer":
        gpu_ram_mb = d.get("gpu_ram") or 0
        return cls(
            id=int(d["id"]),
            dph=float(d.get("dph_total", d.get("dph", 0.0)) or 0.0),
            gpu_name=str(d.get("gpu_name", "?")),
            gpu_ram_gb=round(gpu_ram_mb / 1024, 1) if gpu_ram_mb else 0.0,
            num_gpus=int(d.get("num_gpus", 1) or 1),
            reliability=float(
                d.get("reliability2")
                or d.get("reliability")
                or d.get("expected_reliability")
                or 0.0
            ),
            inet_down=float(d.get("inet_down") or 0.0),
            raw=d,
        )


@dataclass
class ServiceURL:
    name: str
    internal_port: int
    url: str | None


@dataclass
class Instance:
    """A running/stopped instance from `vastai show instances`."""

    id: int
    label: str | None
    status: str
    gpu_name: str
    dph: float
    public_ip: str | None
    ssh_host: str | None
    ssh_port: int | None
    ports: dict | None
    raw: dict

    @classmethod
    def from_raw(cls, d: dict) -> "Instance":
        return cls(
            id=int(d["id"]),
            label=d.get("label"),
            status=str(d.get("actual_status") or d.get("cur_state") or "unknown"),
            gpu_name=str(d.get("gpu_name", "?")),
            dph=float(d.get("dph_total", 0.0) or 0.0),
            public_ip=d.get("public_ipaddr"),
            ssh_host=d.get("ssh_host"),
            ssh_port=d.get("ssh_port"),
            ports=d.get("ports"),
            raw=d,
        )

    def host_port(self, internal_port: int) -> str | None:
        """Public host port mapped to an internal container port.

        VastAI exposes a Docker-style map, e.g.
        ``{"18188/tcp": [{"HostIp": "0.0.0.0", "HostPort": "41234"}]}``.
        Returns None until the instance is running (ports is null when stopped).
        """
        if not self.ports:
            return None
        mapping = self.ports.get(f"{internal_port}/tcp")
        if not mapping:
            return None
        first = mapping[0] if isinstance(mapping, list) else mapping
        return (first or {}).get("HostPort")

    def service_url(self, internal_port: int) -> str | None:
        host_port = self.host_port(internal_port)
        if not self.public_ip or not host_port:
            return None
        return f"http://{self.public_ip}:{host_port}"

    def service_urls(self) -> list[ServiceURL]:
        return [
            ServiceURL(name=name, internal_port=port, url=self.service_url(port))
            for name, port in SERVICE_PORTS.items()
        ]

    def ssh_command(self) -> str | None:
        if not self.ssh_host or not self.ssh_port:
            return None
        return f"ssh -p {self.ssh_port} root@{self.ssh_host}"
