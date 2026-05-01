# Third-Party Notices

Jarvis bundles or builds on the following third-party works. Their respective
upstream LICENSE files, where applicable, are also retained inside the
relevant subdirectories (e.g. `agent/solana-strategy/vendor/...`).

## Solana / trading agents

### Solana Agent Kit v2 — `solana-agent-kit`, `@solana-agent-kit/plugin-token`, `@solana-agent-kit/plugin-defi`, `@solana-agent-kit/adapter-mcp`
- License: Apache-2.0
- Author: SendAI ("sendaifun")
- Source: https://github.com/sendaifun/solana-agent-kit
- Used by `agent/solana-trader/` for Jupiter swap, transfer, balance, and Pump.fun launch routes.

### chainstacklabs/pumpfun-bonkfun-bot
- License: Apache-2.0
- Source: https://github.com/chainstacklabs/pumpfun-bonkfun-bot
- We do not vendor this repo's code directly. The Pump.fun snipe + buy/sell
  builder modules in `agent/solana-strategy/app/tools/strategy/` are inspired
  by chainstacklabs's architecture (PumpPortal listener for new launches,
  remote tx-build via PumpPortal trade-local) but are independently written.
  Listing here as a courtesy / inspiration reference.

### imcrazysteven/Solana-Copy-Trading-Bot
- License: MIT
- Source: https://github.com/imcrazysteven/Solana-Copy-Trading-Bot
- The Jupiter-swap-detection approach in
  `agent/solana-strategy/app/tools/strategy/copy_trade_watcher.py` is a
  clean-room re-implementation in Python. No code lifted directly. Listed
  for attribution courtesy.

## PumpPortal (public API)
- Source: https://pumpportal.fun
- The Pump.fun new-launch scanner subscribes to `wss://pumpportal.fun/api/data`
  and the Pump.fun buy/sell builder calls `https://pumpportal.fun/api/trade-local`.
  These are public, free endpoints. PumpPortal is not affiliated with this
  project.

## Existing Jarvis dependencies
See `package.json` files inside `desktop/`, `agent/solana-trader/`, etc., and
`requirements.txt` files for full dependency manifests. Each package is
distributed under its own license; refer to the upstream project for terms.
