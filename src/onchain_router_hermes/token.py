"""Owner-only access to the non-wallet local proxy bearer."""

from __future__ import annotations

import os
import re
import stat
from pathlib import Path

TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{43}$")
TOKEN_ENV = "ONCHAIN_ROUTER_PROXY_TOKEN"


def profile_directory() -> Path:
    return Path.home() / ".onchain-router"


def token_file() -> Path:
    return profile_directory() / "proxy-token"


def read_proxy_token(path: Path | None = None) -> str:
    candidate = path or token_file()
    metadata = candidate.lstat()
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise RuntimeError("proxy token must be a regular non-symlink file")
    if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
        raise RuntimeError("proxy token must be owned by the current user")
    if stat.S_IMODE(metadata.st_mode) & 0o077:
        raise RuntimeError("proxy token permissions must be 0600")
    if metadata.st_size < 43 or metadata.st_size > 128:
        raise RuntimeError("proxy token file size is invalid")
    value = candidate.read_text(encoding="utf-8").strip()
    if not TOKEN_PATTERN.fullmatch(value):
        raise RuntimeError("proxy token is malformed")
    return value


def refresh_token_environment(path: Path | None = None) -> bool:
    """Load only the validated owner-only bearer into the current Hermes process."""
    os.environ.pop(TOKEN_ENV, None)
    try:
        os.environ[TOKEN_ENV] = read_proxy_token(path)
    except (OSError, RuntimeError):
        return False
    return True
