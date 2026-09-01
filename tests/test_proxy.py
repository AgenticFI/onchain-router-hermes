from pathlib import Path

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
