import argparse
from pathlib import Path

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
