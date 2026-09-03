"""Qualify the repository layout used by Hermes' native Git installer."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def main() -> None:
    root = Path.cwd().resolve()
    with tempfile.TemporaryDirectory(prefix="onchain-router-hermes-git-") as temp:
        home = Path(temp) / "home"
        home.mkdir(mode=0o700)
        os.environ["HERMES_HOME"] = str(home)
        bundled = home / "empty-bundled-plugins"
        bundled.mkdir()
        os.environ["HERMES_BUNDLED_PLUGINS"] = str(bundled)

        from hermes_cli.plugins_cmd import _install_plugin_core

        target, manifest, installed_name = _install_plugin_core(
            root.as_uri(),
            force=True,
            scan_decision_cb=lambda _result: True,
        )
        if (
            installed_name != "onchain-router"
            or manifest.get("manifest_version") is not None
            or manifest.get("api_version") != 1
        ):
            raise SystemExit("native Git install metadata drifted")
        if not (target / "__init__.py").is_file() or not (target / "plugin.yaml").is_file():
            raise SystemExit("native Git install omitted its root entry point or manifest")

        (home / "config.yaml").write_text(
            "plugins:\n  enabled:\n    - onchain-router\n",
            encoding="utf-8",
        )
        from hermes_cli.plugins import get_plugin_manager

        manager = get_plugin_manager()
        manager.discover_and_load(force=True)
        loaded = manager._plugins.get("onchain-router")
        if not loaded or not loaded.enabled or loaded.error:
            raise SystemExit(f"native Git plugin failed to load: {getattr(loaded, 'error', None)}")
        expected_tools = {
            "onchain_router_models",
            "onchain_router_pricing",
            "onchain_router_voices",
            "onchain_router_image_generate",
            "onchain_router_speech_generate",
            "onchain_router_transcribe",
        }
        if not expected_tools.issubset(manager._plugin_tool_names):
            raise SystemExit("native Git install omitted AgenticFI tools")
        if "onchain-router" not in manager._plugin_commands or "onchain-router" not in manager._cli_commands:
            raise SystemExit("native Git install omitted AgenticFI commands")

        from providers import list_providers

        profiles = [profile for profile in list_providers() if profile.name == "onchain-router"]
        if len(profiles) != 1 or profiles[0].fallback_models:
            raise SystemExit("native Git install omitted or weakened the provider profile")

    print("hermes_native_git_install_ok")


if __name__ == "__main__":
    main()
