import os
from pathlib import Path

import pytest

from onchain_router_hermes.token import read_proxy_token, refresh_token_environment

TOKEN = "a" * 43


def write_token(tmp_path: Path, mode: int = 0o600) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "proxy-token"
    path.write_text(f"{TOKEN}\n", encoding="utf-8")
    path.chmod(mode)
    return path


def test_reads_only_owner_only_regular_bearer(tmp_path: Path):
    assert read_proxy_token(write_token(tmp_path)) == TOKEN
    with pytest.raises(RuntimeError, match="0600"):
        read_proxy_token(write_token(tmp_path / "wide", 0o644))


def test_rejects_symlink_and_does_not_keep_unvalidated_environment(tmp_path: Path, monkeypatch):
    target = write_token(tmp_path)
    link = tmp_path / "link"
    link.symlink_to(target)
    with pytest.raises(RuntimeError, match="non-symlink"):
        read_proxy_token(link)
    monkeypatch.setenv("ONCHAIN_ROUTER_PROXY_TOKEN", "hostile")
    assert refresh_token_environment(link) is False
    assert "ONCHAIN_ROUTER_PROXY_TOKEN" not in os.environ
