"""Exercise the installed wheel through official Hermes 0.21.0 discovery."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main(mode: str) -> None:
    home = Path(os.environ["HERMES_HOME"])
    home.mkdir(mode=0o700, parents=True, exist_ok=True)
    bundled = home / "empty-bundled-plugins"
    bundled.mkdir(exist_ok=True)
    os.environ["HERMES_BUNDLED_PLUGINS"] = str(bundled)
    if mode in {"enabled", "general"}:
        (home / "config.yaml").write_text("plugins:\n  enabled:\n    - onchain-router\n", encoding="utf-8")
    elif mode == "disabled":
        (home / "config.yaml").write_text("plugins: {}\n", encoding="utf-8")
    else:
        raise SystemExit("mode must be enabled, disabled, or general")

    from providers import list_providers

    # Provider discovery must run before importing the general manager: the official host's
    # broader CLI module graph may itself request the catalog during import.
    profiles = [profile for profile in list_providers() if profile.name == "onchain-router"]
    from hermes_cli import __version__ as hermes_version
    from hermes_cli.plugins import discover_entrypoint_manifests

    if hermes_version != "0.21.0":
        raise SystemExit(f"unexpected Hermes version: {hermes_version}")
    manifests = [item for item in discover_entrypoint_manifests() if item.name == "onchain-router"]
    if len(manifests) != 1 or manifests[0].kind != "standalone":
        raise SystemExit("Hermes did not discover the standalone entry point")
    if mode == "disabled" and profiles:
        raise SystemExit("disabled pip provider loaded without opt-in")
    if mode in {"enabled", "general"}:
        if len(profiles) != 1:
            raise SystemExit("enabled pip provider was not discovered")
        profile = profiles[0]
        if profile.base_url != "http://127.0.0.1:8402/v1" or profile.fallback_models:
            raise SystemExit("provider boundary or fallback policy drifted")
    if mode == "general":
        from hermes_cli.plugins import get_plugin_manager

        manager = get_plugin_manager()
        manager.discover_and_load(force=True)
        loaded = manager._plugins.get("onchain-router")
        if not loaded or not loaded.enabled or loaded.error:
            raise SystemExit(f"general plugin failed: {getattr(loaded, 'error', None)}")
        expected_tools = {
            "onchain_router_models",
            "onchain_router_pricing",
            "onchain_router_voices",
            "onchain_router_image_generate",
            "onchain_router_speech_generate",
            "onchain_router_transcribe",
        }
        if not expected_tools.issubset(manager._plugin_tool_names):
            raise SystemExit("general plugin tools are missing")
        if "onchain-router" not in manager._plugin_commands or "onchain-router" not in manager._cli_commands:
            raise SystemExit("general plugin commands are missing")
        if "onchain-router:guide" not in manager._plugin_skills:
            raise SystemExit("general plugin skill is missing")
        if "llm_request" not in manager._middleware or len(manager._middleware["llm_request"]) != 1:
            raise SystemExit("stable paid-request middleware is missing")
        identity_context = {
            "request": {"model": "model-a", "messages": [{"role": "user", "content": "private"}]},
            "session_id": "session-1",
            "turn_id": "turn-1",
            "api_request_id": "turn-1:api:1",
            "api_call_count": 1,
            "model": "model-a",
            "provider": "onchain-router",
            "base_url": "http://127.0.0.1:8402/v1",
        }
        identities = manager.invoke_middleware("llm_request", **identity_context)
        repeated = manager.invoke_middleware("llm_request", **identity_context)
        if len(identities) != 1 or identities != repeated:
            raise SystemExit("Hermes retry identity is not stable")
        headers = identities[0].get("request", {}).get("extra_headers", {})
        if not str(headers.get("Idempotency-Key", "")).startswith("hermes-"):
            raise SystemExit("Hermes paid-request identity is missing")
        if headers.get("Cache-Control") != "no-store":
            raise SystemExit("Hermes paid-request cache bypass is missing")
    print(f"hermes_official_discovery_{mode}_ok")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: qualify_official_hermes.py <enabled|disabled|general>")
    main(sys.argv[1])
