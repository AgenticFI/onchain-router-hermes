"""Fixed-version supervisor for the local AgenticFI buyer proxy."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import httpx

from .token import profile_directory, read_proxy_token, refresh_token_environment, token_file

PROXY_PACKAGE = "@agenticfi/onchain-router-proxy"
PROXY_VERSION = "0.1.3"
PROXY_ORIGIN = "http://127.0.0.1:8402"
MAX_CATALOG_BYTES = 4 * 1024 * 1024
START_TIMEOUT_SECONDS = 15.0
PROBE_INTERVAL_SECONDS = 0.1

_lock = threading.RLock()
_process: subprocess.Popen | None = None
_crashed = False


@dataclass(frozen=True)
class ProxyStatus:
    reachable: bool
    origin: str = PROXY_ORIGIN
    managed: bool = False
    pid: int | None = None
    error: str | None = None


def npm_root() -> Path:
    return profile_directory() / "hermes" / "npm"


def _owned_regular_file(path: Path, label: str) -> None:
    metadata = path.lstat()
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise RuntimeError(f"{label} must be a regular non-symlink file")
    if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
        raise RuntimeError(f"{label} must be owned by the current user")


def resolve_proxy_entrypoint(root: Path | None = None) -> Path:
    package_directory = (root or npm_root()) / "node_modules" / "@agenticfi" / "onchain-router-proxy"
    package_json = package_directory / "package.json"
    _owned_regular_file(package_json, "buyer proxy package metadata")
    if package_json.stat().st_size > 16 * 1024:
        raise RuntimeError("buyer proxy package metadata is too large")
    try:
        metadata = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError("buyer proxy package metadata is invalid") from exc
    if metadata.get("name") != PROXY_PACKAGE or metadata.get("version") != PROXY_VERSION:
        raise RuntimeError(f"buyer proxy must be exactly {PROXY_PACKAGE}@{PROXY_VERSION}")
    binary = metadata.get("bin")
    relative = binary.get("onchain-router-proxy") if isinstance(binary, dict) else None
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise RuntimeError("buyer proxy package has no safe executable")
    package_real = package_directory.resolve(strict=True)
    entrypoint = (package_directory / relative).resolve(strict=True)
    if not entrypoint.is_relative_to(package_real):
        raise RuntimeError("buyer proxy executable escapes its package")
    _owned_regular_file(entrypoint, "buyer proxy executable")
    return entrypoint


def probe_proxy(
    *,
    origin: str = PROXY_ORIGIN,
    path: Path | None = None,
    timeout: float = 0.75,
    transport: httpx.BaseTransport | None = None,
) -> bool:
    try:
        token = read_proxy_token(path or token_file())
        with httpx.Client(
            timeout=timeout,
            follow_redirects=False,
            trust_env=False,
            transport=transport,
        ) as client:
            with client.stream(
                "GET",
                f"{origin}/v1/models",
                headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
            ) as response:
                declared = response.headers.get("content-length")
                if declared and declared.isdigit() and int(declared) > MAX_CATALOG_BYTES:
                    return False
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_CATALOG_BYTES:
                        return False
                if response.status_code != 200:
                    return False
        value = json.loads(body)
        return isinstance(value, dict) and isinstance(value.get("data"), list)
    except (OSError, RuntimeError, ValueError, httpx.HTTPError):
        return False


def _child_environment() -> dict[str, str]:
    allowed = (
        "HOME",
        "LANG",
        "LC_ALL",
        "LOGNAME",
        "PATH",
        "SHELL",
        "TMPDIR",
        "USER",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
    )
    return {name: os.environ[name] for name in allowed if name in os.environ}


def _terminate(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)


def ensure_running(
    *,
    autospawn: bool = True,
    probe: Callable[[], bool] | None = None,
    resolve_entrypoint: Callable[[], Path] | None = None,
    popen: Callable[..., subprocess.Popen] = subprocess.Popen,
    which: Callable[[str], str | None] = shutil.which,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    recover_crash: bool = False,
) -> ProxyStatus:
    """Reuse or start one fixed-port proxy. Never downloads or retries a paid call."""
    global _crashed, _process
    probe_fn = probe or (lambda: probe_proxy())
    resolver = resolve_entrypoint or resolve_proxy_entrypoint
    with _lock:
        if probe_fn():
            if recover_crash:
                _crashed = False
            refresh_token_environment()
            managed = _process is not None and _process.poll() is None
            return ProxyStatus(True, managed=managed, pid=_process.pid if managed else None)
        if _process is not None and _process.poll() is not None:
            _process = None
            _crashed = True
        if _crashed and not recover_crash:
            return ProxyStatus(False, error="managed buyer proxy exited; inspect receipts, then restart explicitly")
        if recover_crash:
            _crashed = False
        if not autospawn:
            return ProxyStatus(False, error="buyer proxy is not running; start it in a human terminal")
        node = which("node")
        if not node:
            return ProxyStatus(False, error="Node.js is required to start the local buyer proxy")
        try:
            entrypoint = resolver()
        except (OSError, RuntimeError, ValueError) as exc:
            return ProxyStatus(False, error=str(exc))
        try:
            process = popen(
                [
                    node,
                    str(entrypoint),
                    "--profile",
                    str(profile_directory()),
                    "--port",
                    "8402",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=_child_environment(),
                start_new_session=True,
            )
        except OSError:
            return ProxyStatus(False, error="buyer proxy process could not be started")
        _process = process
        deadline = monotonic() + START_TIMEOUT_SECONDS
        while monotonic() < deadline:
            if process.poll() is not None:
                _process = None
                _crashed = True
                return ProxyStatus(False, error="buyer proxy exited before becoming ready")
            if probe_fn():
                refresh_token_environment()
                return ProxyStatus(True, managed=True, pid=process.pid)
            sleep(PROBE_INTERVAL_SECONDS)
        _terminate(process)
        _process = None
        return ProxyStatus(False, error="buyer proxy did not become ready; no paid request was attempted")


def status() -> ProxyStatus:
    return ensure_running(autospawn=False)


def stop() -> None:
    global _process
    with _lock:
        process = _process
        _process = None
        if process is not None:
            _terminate(process)


def reset_for_tests() -> None:
    """Test-only state cleanup; never removes files."""
    global _crashed
    stop()
    _crashed = False
