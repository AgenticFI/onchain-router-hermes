# Changelog

## Unreleased

- Updated the managed AgenticFI CLI and buyer proxy dependencies to the corrected public npm alpha `0.1.2`.
- Added the root manifest and entry point required by Hermes' native Git installer.
- Added a public `owner/repo` install path, desktop deep link, post-install guidance, and direct Git
  install qualification against the official Hermes host.
- Updated the release build backend to patched `setuptools` `83.0.0`.

## 0.1.0 - public-alpha candidate

- Added native Hermes provider discovery and stable per-call idempotency middleware.
- Added read-only model, pricing, and voice tools.
- Added bounded image, speech, and transcription tools over Buyer Runtime.
- Added in-session status, doctor, discovery, and recovery commands.
- Added exact-version setup/update and confirmation-gated managed-client removal.
- Added a crash latch requiring explicit human restart after an unexpected proxy exit.
- Added wheel inspection, install/update/uninstall qualification, and exact Hermes 0.21.0 host tests.
- Kept wallet keys, x402 signing, policy, settlement, receipts, and recovery out of the adapter.
