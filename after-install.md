# Finish Onchain Router setup

The Hermes plugin is installed and enabled, but it does not create, import, unlock, or fund a
wallet.

Run these from a human-controlled terminal:

```bash
hermes plugins doctor onchain-router --ci
hermes onchain-router setup
```

Then use the installed AgenticFI CLI to create or select a low-balance Buyer Runtime profile,
configure conservative budgets, and unlock it. Restart Hermes and choose provider
`onchain-router` with a model returned by its live picker.

Keep the local proxy on `127.0.0.1`; never expose it through a tunnel or LAN bind. Recover an
ambiguous paid result with the original idempotency key and identical request instead of starting a
new payment.

Guide: https://onchainrouter.dev/docs/hermes
