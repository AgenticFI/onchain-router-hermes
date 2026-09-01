"""Human-operated setup and diagnostics for the Hermes adapter."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .proxy import PROXY_PACKAGE, PROXY_VERSION, ensure_running, npm_root, resolve_proxy_entrypoint, status, stop
from .token import read_proxy_token, token_file

CLI_PACKAGE = "@agenticfi/onchain-router-cli"
CLI_VERSION = "0.1.0"


def _node_version(node: str) -> tuple[int, int, int]:
    result = subprocess.run([node, "--version"], capture_output=True, text=True, check=False)
    match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)\s*", result.stdout)
    if result.returncode != 0 or not match:
        raise RuntimeError("Node.js version could not be determined")
    return tuple(int(part) for part in match.groups())


def _package_metadata(root: Path, scope: str, name: str) -> dict:
    path = root / "node_modules" / scope / name / "package.json"
    metadata = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_size > 16 * 1024:
        raise RuntimeError("installed AgenticFI package metadata is invalid")
    if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
        raise RuntimeError("installed AgenticFI package metadata has the wrong owner")
    return json.loads(path.read_text(encoding="utf-8"))


def _child_environment() -> dict[str, str]:
    return {name: os.environ[name] for name in ("HOME", "LANG", "LC_ALL", "PATH", "TMPDIR", "USER") if name in os.environ}


def install_local_clients() -> Path:
    node = shutil.which("node")
    npm = shutil.which("npm")
    if not node or not npm:
        raise RuntimeError("Node.js and npm are required")
    if _node_version(node) < (20, 18, 0):
        raise RuntimeError("Node.js 20.18 or newer is required")
    root = npm_root()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    result = subprocess.run(
        [
            npm,
            "install",
            "--ignore-scripts",
            "--no-audit",
            "--no-fund",
            "--save-exact",
            f"{PROXY_PACKAGE}@{PROXY_VERSION}",
            f"{CLI_PACKAGE}@{CLI_VERSION}",
        ],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        env=_child_environment(),
    )
    if result.returncode != 0:
        raise RuntimeError("exact AgenticFI client installation failed")
    proxy_meta = _package_metadata(root, "@agenticfi", "onchain-router-proxy")
    cli_meta = _package_metadata(root, "@agenticfi", "onchain-router-cli")
    if proxy_meta.get("version") != PROXY_VERSION or cli_meta.get("version") != CLI_VERSION:
        raise RuntimeError("installed AgenticFI client version is not the approved exact version")
    resolve_proxy_entrypoint(root)
    return root


def _enable_plugin() -> bool:
    hermes = shutil.which("hermes")
    if not hermes:
        return False
    result = subprocess.run(
        [hermes, "plugins", "enable", "onchain-router"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        env=_child_environment(),
    )
    return result.returncode == 0


def _setup(_: argparse.Namespace) -> None:
    root = install_local_clients()
    enabled = _enable_plugin()
    print("AgenticFI Hermes adapter setup complete.")
    print(f"  Exact clients: {root}")
    print(f"  Proxy bearer:  {token_file()} (created by the proxy after human Buyer Runtime setup)")
    print(f"  Plugin enabled: {'yes' if enabled else 'run: hermes plugins enable onchain-router'}")
    print("No wallet was created, imported, unlocked, funded, or charged.")
    print("Next, in a human terminal, run the installed onchain-router CLI setup and unlock commands, then restart Hermes.")


def _doctor(_: argparse.Namespace) -> None:
    checks: list[tuple[str, bool, str]] = []
    try:
        entrypoint = resolve_proxy_entrypoint()
        checks.append(("exact_proxy", True, str(entrypoint)))
    except (OSError, RuntimeError, ValueError) as exc:
        checks.append(("exact_proxy", False, str(exc)))
    try:
        read_proxy_token()
        checks.append(("owner_only_bearer", True, str(token_file())))
    except (OSError, RuntimeError) as exc:
        checks.append(("owner_only_bearer", False, str(exc)))
    current = status()
    checks.append(("proxy_reachable", current.reachable, current.error or current.origin))
    for name, passed, detail in checks:
        print(f"{'PASS' if passed else 'FAIL'} {name}: {detail}")
    if not all(item[1] for item in checks):
        raise SystemExit(1)


def _status(args: argparse.Namespace) -> None:
    current = ensure_running(recover_crash=True) if args.start else status()
    print(json.dumps(current.__dict__, indent=2))
    if not current.reachable:
        raise SystemExit(1)


def _stop(_: argparse.Namespace) -> None:
    stop()
    print("Stopped the managed local proxy, if this adapter owned one.")


def _update(_: argparse.Namespace) -> None:
    root = install_local_clients()
    print(f"Verified and updated exact AgenticFI clients at {root}.")
    print("No wallet, policy, bearer, receipt, or recovery data was changed.")


def _uninstall_clients(args: argparse.Namespace) -> None:
    if not args.confirm:
        raise SystemExit("refusing to remove clients without --confirm")
    root = npm_root()
    proxy_meta = _package_metadata(root, "@agenticfi", "onchain-router-proxy")
    cli_meta = _package_metadata(root, "@agenticfi", "onchain-router-cli")
    if proxy_meta.get("version") != PROXY_VERSION or cli_meta.get("version") != CLI_VERSION:
        raise RuntimeError("refusing to remove an unrecognized AgenticFI client version")
    npm = shutil.which("npm")
    if not npm:
        raise RuntimeError("npm is required")
    stop()
    result = subprocess.run(
        [npm, "uninstall", "--ignore-scripts", "--no-audit", "--no-fund", PROXY_PACKAGE, CLI_PACKAGE],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        env=_child_environment(),
    )
    if result.returncode != 0:
        raise RuntimeError("exact AgenticFI client removal failed")
    print("Removed only the Hermes-managed AgenticFI npm clients.")
    print(f"Kept Buyer Runtime profile, wallet, policy, bearer, and receipts at {root.parent.parent}.")


def register_cli(parser: argparse.ArgumentParser) -> None:
    subcommands = parser.add_subparsers(dest="onchain_router_command")
    setup_parser = subcommands.add_parser("setup", help="Install exact local clients and enable the plugin")
    setup_parser.set_defaults(func=_setup)
    doctor_parser = subcommands.add_parser("doctor", help="Run redacted local checks")
    doctor_parser.set_defaults(func=_doctor)
    status_parser = subcommands.add_parser("status", help="Show local proxy status")
    status_parser.add_argument("--start", action="store_true", help="Start the exact installed proxy if needed")
    status_parser.set_defaults(func=_status)
    stop_parser = subcommands.add_parser("stop", help="Stop only the proxy owned by this adapter")
    stop_parser.set_defaults(func=_stop)
    update_parser = subcommands.add_parser("update", help="Reinstall and verify the approved exact clients")
    update_parser.set_defaults(func=_update)
    uninstall_parser = subcommands.add_parser("uninstall-clients", help="Remove only Hermes-managed npm clients")
    uninstall_parser.add_argument("--confirm", action="store_true", help="Confirm removal of exact managed clients")
    uninstall_parser.set_defaults(func=_uninstall_clients)
    parser.add_argument("--version", action="version", version=__version__)


def handle_cli(args: argparse.Namespace) -> None:
    action = getattr(args, "func", None)
    if action is None:
        print("Usage: hermes onchain-router <setup|doctor|status|stop|update|uninstall-clients>")
        return
    action(args)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="hermes-onchain-router")
    register_cli(parser)
    handle_cli(parser.parse_args(argv))


if __name__ == "__main__":
    main(sys.argv[1:])
