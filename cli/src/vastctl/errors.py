"""Typed errors. Each maps to a clean CLI message + exit code (see main.py)."""

from __future__ import annotations


class VastError(Exception):
    """Base class for all expected, user-facing errors."""


class PreflightError(VastError):
    """vastai CLI missing or not authenticated."""


class VastaiCLIError(VastError):
    """A `vastai` subprocess failed or returned unparseable output."""


class ProfileError(VastError):
    """Profile config missing, malformed, or an unknown profile name."""


class NoOffersError(VastError):
    """No GPU offer matched the search/price constraints."""


class InstanceNotFoundError(VastError):
    """No instance matched the given id or name."""


class ReadinessTimeout(VastError):
    """Instance did not become reachable within the timeout."""

    def __init__(self, message: str, instance=None):
        super().__init__(message)
        self.instance = instance
