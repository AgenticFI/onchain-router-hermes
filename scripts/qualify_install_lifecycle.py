"""No-spend wheel install, update, and uninstall qualification in an isolated venv."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run(args: list[str], *, environment: dict[str, str]) -> str:
    result = subprocess.run(args, capture_output=True, text=True, check=False, env=environment)
    if result.returncode != 0:
        safe = result.stderr
        for name in ("ONCHAIN_ROUTER_PROXY_TOKEN", "PAYMENT_SIGNATURE", "RECEIPT_TOKEN"):
            value = os.environ.get(name)
            if value and len(value) >= 8:
                safe = safe.replace(value, "[redacted]")
        raise SystemExit(f"lifecycle command failed: {args[0]}\n{safe}")
    return result.stdout


def main(wheel: str) -> None:
    archive = Path(wheel).resolve(strict=True)
    uv = shutil.which("uv")
    if not uv:
        raise SystemExit("uv is required for lifecycle qualification")
    with tempfile.TemporaryDirectory(prefix="agenticfi-hermes-lifecycle-") as directory:
        root = Path(directory)
        venv = root / "venv"
        environment = {
            name: os.environ[name]
            for name in ("HOME", "LANG", "LC_ALL", "PATH", "TMPDIR", "USER")
            if name in os.environ
        }
        environment["UV_CACHE_DIR"] = str(root / "uv-cache")
        run([uv, "venv", "--python", sys.executable, "--system-site-packages", str(venv)], environment=environment)
        python = venv / "bin" / "python"
        install = [uv, "pip", "install", "--python", str(python), "--no-deps"]
        run([*install, str(archive)], environment=environment)
        probe = [
            str(python),
            "-c",
            (
                "import importlib.metadata as m, onchain_router_hermes as p; "
                "assert m.version('hermes-plugin-onchain-router') == '0.1.1'; "
                "assert p.__version__ == '0.1.1'"
            ),
        ]
        run(probe, environment=environment)
        run([*install, "--reinstall", str(archive)], environment=environment)
        run(probe, environment=environment)
        run(
            [uv, "pip", "uninstall", "--python", str(python), "hermes-plugin-onchain-router"],
            environment=environment,
        )
        absent = subprocess.run(
            [str(python), "-c", "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('onchain_router_hermes') is None else 1)"],
            check=False,
            env=environment,
        )
        if absent.returncode != 0:
            raise SystemExit("wheel uninstall left the adapter importable")
    print("hermes_install_update_uninstall_ok")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: qualify_install_lifecycle.py <wheel>")
    main(sys.argv[1])
