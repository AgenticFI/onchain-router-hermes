"""Hermes directory-plugin entry point for the AgenticFI Onchain Router.

The GitHub installer loads this repository root as a Python package. Extending the package search
path lets the directory install and the wheel reuse exactly the same reviewed implementation.
Importing this module registers only declarative host metadata; it does not read a wallet, access
the network, start a process, or make a payment.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_IMPLEMENTATION = Path(__file__).resolve().parent / "src" / "onchain_router_hermes"
if not _IMPLEMENTATION.is_dir():
    raise RuntimeError("AgenticFI Hermes implementation directory is missing")
_LOADED_AS_PACKAGE = bool(__package__) and "__path__" in globals()
if _LOADED_AS_PACKAGE:
    __path__.append(str(_IMPLEMENTATION))

__all__ = ["register"]
__version__ = "0.1.1"


def _register_provider_side_effect() -> None:
    if not _LOADED_AS_PACKAGE:
        return
    from .provider import register_profile

    try:
        register_profile()
    except ModuleNotFoundError as exc:
        if exc.name not in {"providers", "providers.base"}:
            raise


_register_provider_side_effect()


def register(ctx: Any = None) -> None:
    if ctx is None or not _LOADED_AS_PACKAGE:
        return
    from .plugin import register_host_plugin

    register_host_plugin(ctx)
