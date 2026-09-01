"""Official Hermes model-provider registration."""

from __future__ import annotations


def register_profile():
    from providers import register_provider
    from providers.base import ProviderProfile

    profile = ProviderProfile(
        name="onchain-router",
        aliases=("agenticfi",),
        display_name="AgenticFI Onchain Router",
        description="Policy-bounded, receipt-backed LLM access paid with USDC on Base",
        signup_url="https://llm.agenticfi.wtf/docs/hermes",
        env_vars=("ONCHAIN_ROUTER_PROXY_TOKEN",),
        base_url="http://127.0.0.1:8402/v1",
        models_url="http://127.0.0.1:8402/v1/models",
        auth_type="api_key",
        api_mode="chat_completions",
        supports_health_check=True,
        supports_vision=True,
        fallback_models=(),
    )
    register_provider(profile)
    return profile
