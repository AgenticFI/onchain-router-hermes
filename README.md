# AgenticFI Onchain Router for Hermes Agent

Use Onchain Router as a native Hermes model provider and as a small set of bounded media tools. The
plugin connects only to the authenticated local Buyer Runtime proxy on `127.0.0.1`; wallet and
payment authority remain outside Hermes and under human-owned local policy.

## Release status

Version `0.1.0` is a private alpha source candidate. It is not published or production-qualified.
Building the wheel, installing it in a clean environment, discovering the provider, and running
fake-loopback tests do not unlock a wallet, make a paid request, deploy a service, or spend USDC.

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
| `/onchain-router status` | Redacted local readiness | Free |
| `hermes onchain-router ...` | Human setup, doctor, status, and managed-proxy stop | Free |

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

The official-host qualification installs the built wheel, enables its entry point in an isolated
Hermes home, and checks both model-provider and ordinary plugin discovery against Hermes `0.21.0`.
It uses no wallet or public endpoint.

## Installation and setup

After the package is published, installation is two explicit human actions:

```bash
pip install hermes-plugin-onchain-router==0.1.0
hermes-onchain-router setup
```

`setup` installs only these exact npm clients in `~/.onchain-router/hermes/npm` with lifecycle
scripts disabled:

```text
@agenticfi/onchain-router-proxy@0.1.0
@agenticfi/onchain-router-cli@0.1.0
```

It enables the Hermes plugin when the `hermes` executable is available. It deliberately does not
start the proxy or create, import, unlock, fund, or charge a wallet. Complete Buyer Runtime setup
and unlock separately in a human terminal using the installed AgenticFI CLI, then restart Hermes.
The proxy creates the non-wallet owner-only bearer when it starts. Select provider
`onchain-router` plus a model from the live picker.

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

- Plugin missing: run `hermes plugins enable onchain-router`, then restart Hermes.
- Provider has no models: run `hermes-onchain-router doctor`, unlock Buyer Runtime in a human
  terminal, and restart Hermes.
- Exact client missing: rerun `hermes-onchain-router setup`; it never installs `latest`.
- Port occupied: stop the unrelated process or start the expected proxy. The plugin never scans an
  alternate port.
- Ambiguous result: do not use a new key or model. Inspect receipts and recover with the original
  key and identical body.

Documentation: <https://llm.agenticfi.wtf/docs/hermes>

Support: <https://github.com/AgenticFI/onchain-router-hermes/issues>

Security reports: <https://github.com/AgenticFI/onchain-router-hermes/security/policy>

## License

MIT. See [LICENSE](./LICENSE) and [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md).
