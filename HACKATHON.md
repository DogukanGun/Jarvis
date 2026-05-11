## What are you building, and who is it for?

Jarvis is a sovereign AI desktop agent that runs entirely on your machine, speaks plain English, and actually executes things on your behalf — trading tokens on Solana, researching topics, watching your camera for intruders, reading contracts, reviewing code, and building memory across every session. Your keys never leave your device. No subscription. No cloud.

The desktop app is version one. The real goal is open-source smart glasses — hardware anyone can manufacture, running Jarvis as the operating intelligence. Schematics and BOM will be fully open. Software is MIT licensed.

Built for two groups: crypto-native users who want an AI that trades and manages a wallet without trusting a third party with their keys, and anyone who wants a capable personal AI that does not phone home or hand their data to a cloud provider.

---

## Why did you decide to build this, and why build it now?

Every AI tool makes the same deal: you get intelligence, they get your data, your keys, and a monthly fee. That deal gets worse as AI gets more capable — the more powerful it is, the more dangerous it is to route your actions through someone else's server.

We built Jarvis because that deal should not exist. Your keys never leave your machine. Your trades, contracts, and conversations belong to you.

The timing is specific. Three things converged: local inference became viable (Ollama runs capable models on a laptop, no cloud required), Solana matured as a DeFi execution layer, and smart glasses hardware dropped to a price point where an open-source design is actually buildable. The window to build a sovereign AI agent that is also a real product just opened. We are building through it.

---

## What technologies are you using or integrating with?

**Desktop & UI**
- Electron 39 + React 19 + TypeScript — native cross-platform app (macOS, Windows, Linux)
- Next.js 14 + Framer Motion — landing page, deployed on Vercel

**Agent Mesh — 10 specialised microservices**
- Python + Flask / FastAPI — Router (central orchestrator), Strategy engine,
  Legal RAG, Thinker research pipeline, Vision, Swiss Army Knife, Memory worker
- Node.js + Fastify — Solana Trader agent
- Apache Kafka — async event bus; the Router forwards agent lifecycle events
  to the desktop in real time over WebSocket

**Solana & DeFi**
- Solana Web3.js + SPL Token — wallet, signing, token transfers
- Solana Agent Kit v2 — high-level on-chain actions
- Jupiter — token swap aggregation
- Pump.fun — token launch
- Loopback signer — a private HTTP server inside the Electron main process;
  agents request transaction signatures via bearer-token auth so private keys
  are never exposed to the network

**AI & Inference**
- Ollama — local LLM inference, no cloud required
- OpenAI Whisper — speech-to-text for voice input
- YOLOv8 — real-time object detection for guard mode camera surveillance
- RAG pipeline — PDF/text ingestion, vector search, LLM synthesis for the
  legal document agent
- Mem0 — semantic memory layer across sessions

**Security & Auth**
- macOS Touch ID / Face ID via Electron's native biometric API
- AES-256 encrypted wallet vault, PIN-protected, bcrypt-hashed
- BIP39 mnemonic derivation, Ed25519 HD keys

**Infrastructure**
- Docker Compose — Kafka, Zookeeper, MinIO, Ollama
- MinIO — S3-compatible artifact and memory blob storage
