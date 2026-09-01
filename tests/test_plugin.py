from pathlib import Path

import onchain_router_hermes


class FakeContext:
    def __init__(self):
        self.tools = []
        self.hooks = []
        self.commands = []
        self.cli = []
        self.skills = []
        self.unloads = []

    def register_tool(self, **kwargs):
        self.tools.append(kwargs)

    def register_hook(self, name, handler):
        self.hooks.append((name, handler))

    def register_command(self, **kwargs):
        self.commands.append(kwargs)

    def register_cli_command(self, **kwargs):
        self.cli.append(kwargs)

    def register_skill(self, **kwargs):
        assert Path(kwargs["path"]).is_file()
        self.skills.append(kwargs)

    def on_unload(self, handler):
        self.unloads.append(handler)


def test_general_entrypoint_registers_expected_bounded_surfaces(monkeypatch):
    monkeypatch.setattr("onchain_router_hermes.plugin.refresh_token_environment", lambda: False)
    context = FakeContext()
    onchain_router_hermes.register(context)
    assert {tool["name"] for tool in context.tools} == {
        "onchain_router_models",
        "onchain_router_pricing",
        "onchain_router_voices",
        "onchain_router_image_generate",
        "onchain_router_speech_generate",
        "onchain_router_transcribe",
    }
    assert [name for name, _ in context.hooks] == ["pre_llm_call"]
    assert [command["name"] for command in context.commands] == ["onchain-router"]
    assert [command["name"] for command in context.cli] == ["onchain-router"]
    assert [skill["name"] for skill in context.skills] == ["guide"]
    assert len(context.unloads) == 1
