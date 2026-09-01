# Security policy

## Boundary

- Only `http://127.0.0.1:8402` is used.
- The plugin reads only the owner-only non-wallet proxy bearer and places it in the trusted Hermes
  process environment for the provider transport. It never logs or returns the value.
- Wallet keys, mnemonics, payment signatures, raw x402 payloads, provider keys, receipt
  capabilities, backend source, and production credentials are outside this repository.
- Host startup never downloads code. Human `setup` installs exact npm versions with lifecycle
  scripts disabled; runtime resolves and validates their package metadata and executable path.
- The supervisor starts one fixed-port child, never scans ports or runs a heartbeat, and stops only
  its own child. It never replays a paid request.
- Paid tools require an explicit idempotency key, validate inputs before proxy handoff, make one
  outbound call, bound responses, and classify transport uncertainty for human review.

## Supported systems

The private alpha targets macOS and Linux with Python 3.11–3.13, Hermes Agent 0.21.0, and Node.js
20.18 or newer. Windows is not advertised until equivalent process, filesystem, and secret tests
pass.

## Reporting

Report vulnerabilities privately through
<https://github.com/AgenticFI/onchain-router-hermes/security/advisories/new>. Do not include wallet
keys, proxy bearers, payment payloads, receipt capabilities, prompts, media, or model output.
