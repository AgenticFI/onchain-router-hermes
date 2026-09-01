from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest

from onchain_router_hermes import proxy


class FakeProcess:
    def __init__(self):
        self.pid = 4242
        self.returncode = None
        self.terminated = 0

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated += 1
        self.returncode = 0

    def kill(self):
        self.returncode = -9

    def wait(self, timeout=None):
        return self.returncode


@pytest.fixture(autouse=True)
def clean_supervisor():
    proxy.reset_for_tests()
    yield
    proxy.reset_for_tests()


def test_reuses_external_proxy_without_process_start():
    called = 0

    def popen(*args, **kwargs):
        nonlocal called
        called += 1
        return FakeProcess()

    current = proxy.ensure_running(probe=lambda: True, popen=popen)
    assert current.reachable is True
    assert current.managed is False
    assert called == 0
    proxy.stop()
    assert called == 0


def test_starts_one_exact_child_and_stops_only_that_child():
    probes = iter([False, True])
    process = FakeProcess()
    invocations = []

    def popen(args, **kwargs):
        invocations.append((args, kwargs))
        return process

    current = proxy.ensure_running(
        probe=lambda: next(probes),
        resolve_entrypoint=lambda: Path("/safe/onchain-router-proxy.js"),
        popen=popen,
        which=lambda _: "/safe/node",
        monotonic=lambda: 0,
        sleep=lambda _: None,
    )
    assert current == proxy.ProxyStatus(True, managed=True, pid=4242)
    assert invocations[0][0] == [
        "/safe/node",
        "/safe/onchain-router-proxy.js",
        "--profile",
        str(Path.home() / ".onchain-router"),
        "--port",
        "8402",
    ]
    assert "NODE_AUTH_TOKEN" not in invocations[0][1]["env"]
    proxy.stop()
    assert process.terminated == 1


def test_missing_exact_package_fails_without_download_or_spawn():
    called = 0

    def popen(*args, **kwargs):
        nonlocal called
        called += 1
        return FakeProcess()

    current = proxy.ensure_running(
        probe=lambda: False,
        resolve_entrypoint=lambda: (_ for _ in ()).throw(RuntimeError("exact package missing")),
        popen=popen,
        which=lambda _: "/safe/node",
    )
    assert current.reachable is False
    assert current.error == "exact package missing"
    assert called == 0


def test_crashed_managed_proxy_is_latched_until_explicit_human_restart():
    first = FakeProcess()
    second = FakeProcess()
    processes = iter([first, second])
    spawns = []
    probes = iter([False, True, False, False, True])

    def popen(*args, **kwargs):
        process = next(processes)
        spawns.append(process)
        return process

    assert proxy.ensure_running(
        probe=lambda: next(probes), resolve_entrypoint=lambda: Path("/safe/proxy.js"),
        popen=popen, which=lambda _: "/safe/node", monotonic=lambda: 0, sleep=lambda _: None,
    ).reachable
    first.returncode = 1
    blocked = proxy.ensure_running(probe=lambda: next(probes), popen=popen, which=lambda _: "/safe/node")
    assert blocked.reachable is False
    assert "restart explicitly" in blocked.error
    assert len(spawns) == 1
    recovered = proxy.ensure_running(
        recover_crash=True, probe=lambda: next(probes), resolve_entrypoint=lambda: Path("/safe/proxy.js"),
        popen=popen, which=lambda _: "/safe/node", monotonic=lambda: 0, sleep=lambda _: None,
    )
    assert recovered.reachable is True
    assert len(spawns) == 2


def test_concurrent_start_requests_create_one_child():
    process = FakeProcess()
    calls = 0
    healthy = False

    def probe():
        return healthy

    def popen(*args, **kwargs):
        nonlocal calls, healthy
        calls += 1
        healthy = True
        return process

    def start():
        return proxy.ensure_running(
            probe=probe, resolve_entrypoint=lambda: Path("/safe/proxy.js"), popen=popen,
            which=lambda _: "/safe/node", monotonic=lambda: 0, sleep=lambda _: None,
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: start(), range(4)))
    assert all(item.reachable for item in results)
    assert calls == 1


def test_start_timeout_terminates_the_owned_child_without_port_scanning():
    process = FakeProcess()
    times = iter([0, 16])
    current = proxy.ensure_running(
        probe=lambda: False,
        resolve_entrypoint=lambda: Path("/safe/proxy.js"),
        popen=lambda *args, **kwargs: process,
        which=lambda _: "/safe/node",
        monotonic=lambda: next(times, 16),
        sleep=lambda _: None,
    )
    assert current.reachable is False
    assert "no paid request" in current.error
    assert process.terminated == 1


def test_child_environment_excludes_wallet_provider_and_registry_secrets(monkeypatch):
    monkeypatch.setenv("WALLET_PRIVATE_KEY", "secret")
    monkeypatch.setenv("GOOGLE_API_KEY", "secret")
    monkeypatch.setenv("NPM_TOKEN", "secret")
    environment = proxy._child_environment()
    assert "WALLET_PRIVATE_KEY" not in environment
    assert "GOOGLE_API_KEY" not in environment
    assert "NPM_TOKEN" not in environment


def test_explicit_stop_does_not_create_a_crash_latch():
    process = FakeProcess()
    probes = iter([False, True])
    assert proxy.ensure_running(
        probe=lambda: next(probes), resolve_entrypoint=lambda: Path("/safe/proxy.js"),
        popen=lambda *args, **kwargs: process, which=lambda _: "/safe/node",
        monotonic=lambda: 0, sleep=lambda _: None,
    ).reachable
    proxy.stop()
    current = proxy.ensure_running(autospawn=False, probe=lambda: False)
    assert current.error == "buyer proxy is not running; start it in a human terminal"
