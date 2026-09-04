"""Hermes entry point for Onchain Router.

Hermes imports this module during provider discovery and calls ``register``
with a PluginContext during ordinary plugin loading. Provider registration is
declarative and performs no file, network, process, wallet, or payment action.
"""

from __future__ import annotations

from typing import Any

__all__ = ["register"]
__version__ = "0.2.0"


def _register_provider_side_effect() -> None:
    from .provider import register_profile

    try:
        register_profile()
    except ModuleNotFoundError as exc:
        # The standalone human CLI remains usable before Hermes is installed.
        if exc.name not in {"providers", "providers.base"}:
            raise


_register_provider_side_effect()


def register(ctx: Any = None) -> None:
    if ctx is None:
        return
    from .plugin import register_host_plugin

    register_host_plugin(ctx)
