import argparse
import subprocess
from pathlib import Path

import pytest

from onchain_router_hermes import cli


def test_setup_installs_and_enables_without_starting_proxy(monkeypatch, capsys, tmp_path):
    install_root = tmp_path / "npm"
    monkeypatch.setattr(cli, "install_local_clients", lambda: install_root)
    monkeypatch.setattr(cli, "_enable_plugin", lambda: True)
    monkeypatch.setattr(cli, "token_file", lambda: Path("/redacted/proxy-token"))
    monkeypatch.setattr(
        cli,
        "ensure_running",
        lambda: (_ for _ in ()).throw(AssertionError("setup must not start the proxy")),
    )

    cli._setup(argparse.Namespace())

    output = capsys.readouterr().out
    assert "Plugin enabled: yes" in output
    assert "No wallet was created, imported, unlocked, funded, or charged." in output
    assert "created by the proxy after human Buyer Runtime setup" in output


def test_update_reinstalls_exact_clients_without_touching_wallet_state(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(cli, "install_local_clients", lambda: tmp_path / "npm")
    cli._update(argparse.Namespace())
    output = capsys.readouterr().out
    assert "updated exact Onchain Router clients" in output
    assert "No wallet" in output


def test_uninstall_requires_confirmation_before_inspection_or_process_actions(monkeypatch):
    monkeypatch.setattr(cli, "_package_metadata", lambda *args: (_ for _ in ()).throw(AssertionError("no inspection")))
    with pytest.raises(SystemExit, match="--confirm"):
        cli._uninstall_clients(argparse.Namespace(confirm=False))


def test_confirmed_uninstall_removes_only_exact_managed_clients(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(cli, "npm_root", lambda: tmp_path / "profile" / "hermes" / "npm")
    monkeypatch.setattr(
        cli,
        "_package_metadata",
        lambda _root, _scope, name: {"version": cli.PROXY_VERSION if name == "onchain-router-proxy" else cli.CLI_VERSION},
    )
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/safe/npm" if name == "npm" else None)
    monkeypatch.setattr(cli, "stop", lambda: None)
    calls = []
    monkeypatch.setattr(cli.subprocess, "run", lambda args, **kwargs: calls.append((args, kwargs)) or subprocess.CompletedProcess(args, 0))
    cli._uninstall_clients(argparse.Namespace(confirm=True))
    assert calls[0][0][-2:] == [cli.PROXY_PACKAGE, cli.CLI_PACKAGE]
    assert calls[0][1]["env"].get("WALLET_PRIVATE_KEY") is None
    output = capsys.readouterr().out
    assert "Removed only" in output
    assert "Kept Buyer Runtime profile" in output
