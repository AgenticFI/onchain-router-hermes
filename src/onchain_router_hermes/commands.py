"""Read-only in-session discovery, status, and recovery commands."""

from __future__ import annotations

from . import tools
from .proxy import resolve_proxy_entrypoint, status
from .token import read_proxy_token

HELP = (
    "Onchain Router commands:\n"
    "  /onchain-router status   Show local proxy readiness\n"
    "  /onchain-router doctor   Run redacted local checks\n"
    "  /onchain-router models   Show policy-filtered models\n"
    "  /onchain-router pricing  Show current pass-through pricing\n"
    "  /onchain-router voices   Show available speech voices\n"
    "  /onchain-router recovery Explain safe same-key recovery\n"
    "  /onchain-router help     Show this message\n\n"
    "Choose provider 'onchain-router' and a model from the live picker for chat. "
    "Wallet setup, unlock, funding, policy, backup, and recovery remain human terminal actions."
)


def dispatch(raw_args: str) -> str:
    command = (raw_args or "").strip().lower()
    if command in {"", "help", "?"}:
        return HELP
    if command == "recovery":
        return (
            "Ambiguous paid-call recovery:\n"
            "1. Do not retry with a new key or a different model.\n"
            "2. Inspect Buyer Runtime receipts from a human terminal.\n"
            "3. Recover with the original idempotency key and identical request.\n"
            "4. Never paste a receipt capability, proxy bearer, or wallet secret into chat."
        )
    if command == "doctor":
        checks = []
        try:
            read_proxy_token()
            checks.append("PASS owner_only_bearer: owner-only token is valid")
        except (OSError, RuntimeError):
            checks.append("FAIL owner_only_bearer: token is missing or unsafe")
        try:
            resolve_proxy_entrypoint()
            checks.append("PASS exact_proxy: exact pinned entrypoint is valid")
        except (OSError, RuntimeError, ValueError):
            checks.append("FAIL exact_proxy: package is missing, unsafe, or the wrong version")
        current = status()
        checks.append(f"{'PASS' if current.reachable else 'FAIL'} proxy_reachable: {current.error or current.origin}")
        return "\n".join(checks)
    discovery = {
        "models": tools.models,
        "pricing": tools.pricing,
        "voices": tools.voices,
    }
    if command in discovery:
        output = discovery[command]()
        return output if len(output) <= 16_000 else f"{output[:16_000]}\n…output truncated"
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
