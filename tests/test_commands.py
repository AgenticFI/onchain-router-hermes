from onchain_router_hermes import commands
from onchain_router_hermes.proxy import ProxyStatus


def test_help_lists_discovery_diagnostics_and_recovery_without_side_effects(monkeypatch):
    monkeypatch.setattr(commands, "status", lambda: (_ for _ in ()).throw(AssertionError("no probe")))
    output = commands.dispatch("help")
    assert "doctor" in output
    assert "models" in output
    assert "recovery" in output
    assert "human terminal" in output


def test_status_is_redacted(monkeypatch):
    monkeypatch.setattr(commands, "status", lambda: ProxyStatus(True, managed=True, pid=42))
    output = commands.dispatch("status")
    assert "Reachable: true" in output
    assert "Managed:   true" in output
    assert "PID:       42" in output


def test_doctor_reports_only_redacted_local_facts(monkeypatch):
    monkeypatch.setattr(commands, "read_proxy_token", lambda: "s" * 43)
    monkeypatch.setattr(commands, "resolve_proxy_entrypoint", lambda: "/safe/proxy.js")
    monkeypatch.setattr(commands, "status", lambda: ProxyStatus(True))
    output = commands.dispatch("doctor")
    assert "PASS owner_only_bearer" in output
    assert "PASS exact_proxy" in output
    assert "PASS proxy_reachable" in output
    assert "s" * 43 not in output


def test_discovery_commands_use_only_read_only_tools(monkeypatch):
    calls = []
    monkeypatch.setattr(commands.tools, "models", lambda: calls.append("models") or '{"ok":true}')
    monkeypatch.setattr(commands.tools, "pricing", lambda: calls.append("pricing") or '{"ok":true}')
    monkeypatch.setattr(commands.tools, "voices", lambda: calls.append("voices") or '{"ok":true}')
    assert commands.dispatch("models") == '{"ok":true}'
    assert commands.dispatch("pricing") == '{"ok":true}'
    assert commands.dispatch("voices") == '{"ok":true}'
    assert calls == ["models", "pricing", "voices"]


def test_recovery_requires_the_original_key_and_human_review():
    output = commands.dispatch("recovery")
    assert "original idempotency key" in output
    assert "Never paste" in output


def test_unknown_command_does_not_expose_a_wallet_surface():
    output = commands.dispatch("wallet export")
    assert "Unknown subcommand" in output
    assert "wallet export" in output
    assert "human terminal" in output
