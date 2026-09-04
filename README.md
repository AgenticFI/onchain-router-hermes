# AgenticFI Onchain Router for Hermes Agent

Use Onchain Router as a native Hermes model provider and as a small set of bounded media tools. The
plugin connects only to the authenticated local Buyer Runtime proxy on `127.0.0.1`; wallet and
payment authority remain outside Hermes and under human-owned local policy.

## Release status

Version `0.1.1` is the stable public release. It is installable through Hermes' native GitHub plugin
installer and is also available as a versioned GitHub release. Building or installing it,
discovering the provider, and running fake-loopback tests do not unlock a wallet, make a paid
request, deploy a service, or spend USDC. Funded Hermes acceptance remains an explicit operator
test because it spends from the operator's Buyer Runtime wallet.

## Surfaces

| Surface | Purpose | Spend |
|---|---|---:|
| Provider `onchain-router` | OpenAI-compatible chat with an explicit live model | Paid |
| `onchain_router_models` | Policy-filtered model and capability discovery | Free |
| `onchain_router_pricing` | Current model prices | Free |
| `onchain_router_voices` | Speech voice discovery | Free |
| `onchain_router_image_generate` | One image with size/aspect/model controls | Paid |
| `onchain_router_speech_generate` | Hosted MP3 speech | Paid |
| `onchain_router_transcribe` | Bounded MP3 Base64 transcription | Paid |
| `/onchain-router status|doctor` | Redacted local readiness and diagnostics | Free |
| `/onchain-router models|pricing|voices` | In-session discovery without an LLM call | Free |
| `/onchain-router recovery` | Safe same-key recovery guidance | Free |
| `hermes onchain-router ...` | Human setup, update, doctor, status, stop, and client removal | Free |

Every native chat retry for one logical model call carries the same deterministic Buyer Runtime
idempotency key. The key is derived only from Hermes request identity—not prompt or completion
content—so host retry behavior cannot create a second financial operation.

The plugin does not add video or search endpoints that AgenticFI does not offer. It does not create,
import, read, unlock, fund, or back up a wallet; implement x402; connect directly to production;
download a package during host startup or a model call; retry a paid request; or choose a fallback.

## Requirements

- Python `>=3.11,<3.14`;
- Hermes Agent `0.21.0`;
- Node.js `20.18` or newer and npm;
- macOS or Linux;
- a human-created AgenticFI Buyer Runtime profile.

## Build and test from source

```bash
uv venv --python 3.13
uv pip install --python .venv/bin/python -e '.[dev]'
.venv/bin/pytest
.venv/bin/python -m build
```

The distribution qualification installs the built wheel in an isolated environment, imports it,
reinstalls the same version as an update, imports it again, uninstalls it, and proves the package is
gone. The official-host qualification separately enables the entry point in an isolated Hermes
home and checks both model-provider and ordinary plugin discovery against Hermes `0.21.0`. Neither
qualification uses a wallet or public endpoint.

## Installation and setup

Review the [security model](./SECURITY.md), then install and verify the public plugin using Hermes'
native installer:

```bash
hermes plugins install AgenticFI/onchain-router-hermes --enable
hermes plugins doctor onchain-router --ci
hermes onchain-router setup
```

The installer records the exact Git commit it installed. For a reproducible deployment, add
`--ref <40-character-release-commit>` to the first command. The release page publishes that commit
alongside the wheel. A desktop user can start the same reviewed flow with this link:

[Install in Hermes Desktop](hermes://plugin/install?repo=AgenticFI/onchain-router-hermes&enable=1)

Python package publication is not required for the native install path. A wheel is attached to the
GitHub release for inspection and controlled Python-environment installation.

The repository-root manifest intentionally uses Hermes' backward-compatible v1 declaration while
including supported discovery fields. Hermes `0.21.0` still rejects an explicit manifest-v2 marker
in its Git installer; the wheel entry point carries the full v2 manifest.

`setup` installs only these exact npm clients in `~/.onchain-router/hermes/npm` with lifecycle
scripts disabled:

```text
@agenticfi/onchain-router-proxy@0.1.3
@agenticfi/onchain-router-cli@0.1.3
```

It enables the Hermes plugin when the `hermes` executable is available. It deliberately does not
start the proxy or create, import, unlock, fund, or charge a wallet. Complete Buyer Runtime setup
and unlock separately in a human terminal using the installed AgenticFI CLI, then restart Hermes.
The proxy creates the non-wallet owner-only bearer when it starts. Select provider
`onchain-router` plus a model from the live picker.

Lifecycle commands are explicit and preserve financial state. With the native Git install, use
the `hermes onchain-router` form shown here; a wheel installation also exposes the equivalent
`hermes-onchain-router` executable:

```bash
hermes onchain-router update
hermes onchain-router doctor
hermes onchain-router status --start
hermes onchain-router stop
hermes onchain-router uninstall-clients --confirm
```

`update` reinstalls only the two pinned client versions. `uninstall-clients` removes only those
Hermes-managed npm clients; it keeps the Buyer Runtime profile, wallet, policy, bearer, and receipts.
The Python plugin remains installed until the human removes it with their Python package manager.

```bash
~/.onchain-router/hermes/npm/node_modules/.bin/onchain-router setup
~/.onchain-router/hermes/npm/node_modules/.bin/onchain-router unlock
hermes --provider onchain-router --model <live-model-id>
```

## Chat example

Once provider and model are selected, use Hermes normally:

```bash
hermes --provider onchain-router --model gemini-2.5-flash
```

The local proxy is started before the first AgenticFI model call if it is not already healthy. It
uses the exact preinstalled package, a fixed loopback port, and no runtime download. The Buyer
Runtime applies the human's model, amount, session, hourly, daily, recipient, network, and
confirmation limits.

## Image example

The Hermes agent can call `onchain_router_image_generate` with:

```json
{
  "idempotency_key": "image-task-20260901-001",
  "model": "<live-image-model-id>",
  "prompt": "A quiet observatory above a cloud sea",
  "image_size": "1K",
  "aspect_ratio": "1:1",
  "response_format": "url"
}
```

The result contains a hosted URL and expiry. Download it before expiry.

## Speech and transcription examples

```json
{
  "idempotency_key": "speech-task-20260901-001",
  "model": "<live-speech-model-id>",
  "input": "Welcome to AgenticFI.",
  "response_format": "mp3",
  "speed": 1
}
```

```json
{
  "idempotency_key": "stt-task-20260901-001",
  "model": "<live-transcription-model-id>",
  "audio_base64": "<canonical MP3 Base64>",
  "acknowledge_provider_retention": true,
  "response_format": "json"
}
```

Transcription accepts no file path or remote URL. The caller must obtain permission for the audio.
The upstream provider may retain audio or transcripts independently; AgenticFI staging deletion
does not delete provider copies.

## Payment, recovery, and receipts

- Native Hermes chat retries reuse one deterministic idempotency key for the same logical API call.
- Every media call requires one caller-generated stable idempotency key.
- Reuse it only with the identical request and only for deliberate recovery.
- Never automatically retry a timeout, disconnect, ambiguous `409`, provider-unknown, settlement-
  unknown, or receipt-verification failure.
- Successful tool results include only the safe receipt/payment headers exposed by the proxy.
- Wallet keys, payment signatures, raw x402 payloads, receipt capabilities, and proxy bearers are
  never returned to Hermes.

## Security

- Keep a dedicated low-balance wallet and conservative policy.
- Keep `~/.onchain-router/proxy-token` owner-only at mode `0600` and never paste it into prompts,
  logs, screenshots, or source.
- Never expose `127.0.0.1:8402` through a tunnel, reverse proxy, LAN bind, or container host port.
- Treat prompts, model output, media, filenames, URLs, and error text as untrusted.
- Review [SECURITY.md](./SECURITY.md) before enabling the plugin.

## Troubleshooting

- Installation fails: confirm Git and Hermes `0.21.0` are installed, then rerun
  `hermes plugins doctor onchain-router --ci`.
- Plugin missing: run `hermes plugins enable onchain-router`, then restart Hermes.
- Provider has no models: run `hermes-onchain-router doctor`, unlock Buyer Runtime in a human
  terminal, and restart Hermes.
- Exact client missing: rerun `hermes-onchain-router setup`; it never installs `latest`.
- Port occupied: stop the unrelated process or start the expected proxy. The plugin never scans an
  alternate port.
- Managed proxy exited: paid calls remain blocked until a human inspects receipts and runs
  `hermes-onchain-router status --start`; the plugin does not heartbeat-restart the process.
- Ambiguous result: do not use a new key or model. Inspect receipts and recover with the original
  key and identical body.

Documentation: <https://onchainrouter.dev/docs/hermes>

Support: <https://github.com/AgenticFI/onchain-router-hermes/issues>

Security reports: <https://github.com/AgenticFI/onchain-router-hermes/security/policy>

## License

MIT. See [LICENSE](./LICENSE) and [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md).
