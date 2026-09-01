"""Read-only in-session status command."""

from __future__ import annotations

from .proxy import status

HELP = (
    "Onchain Router commands:\n"
    "  /onchain-router status   Show local proxy readiness\n"
    "  /onchain-router help     Show this message\n\n"
    "Choose provider 'onchain-router' and a model from the live picker for chat. "
    "Wallet setup, unlock, funding, policy, backup, and recovery remain human terminal actions."
)


def dispatch(raw_args: str) -> str:
    command = (raw_args or "").strip().lower()
    if command in {"", "help", "?"}:
        return HELP
    if command != "status":
        return f"Unknown subcommand: {command!r}\n{HELP}"
    current = status()
    return (
        "Onchain Router local proxy\n"
        f"  Origin:    {current.origin}\n"
        f"  Reachable: {str(current.reachable).lower()}\n"
        f"  Managed:   {str(current.managed).lower()}\n"
        f"  PID:       {current.pid if current.pid is not None else '—'}\n"
        f"  Error:     {current.error or '—'}"
    )
