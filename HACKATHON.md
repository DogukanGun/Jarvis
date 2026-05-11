## What are you building, and who is it for?

Jarvis is a sovereign AI desktop agent — a native app that runs entirely on
your machine, speaks plain English, and actually executes things on your
behalf. It combines a biometric-secured Solana wallet, a mesh of specialised
AI agents, and a real-time chat interface into a single app you install and own.

It can trade tokens autonomously on Solana (Jupiter swaps, Pump.fun launches,
automated strategy with a panic-sell watchdog), research any topic and produce
a structured report, watch your camera and lock your screen when it detects an
intruder, read and answer questions about legal contracts, review code for
security issues, and build persistent memory of every conversation and decision
across sessions.

The desktop app is version one. The end goal is **open-source smart glasses**
— hardware anyone can manufacture themselves, running Jarvis as the operating
intelligence. The hardware schematics and bill of materials will be fully open,
and the software is already MIT licensed.

It is built for two overlapping groups: crypto-native users who want an AI
that can execute trades and manage a wallet without trusting a third party with
their keys, and anyone who wants a capable personal AI that does not phone
home, does not require a subscription, and does not hand their data to a cloud
provider. The longer-term buyer is the person who will wear the glasses —
someone who wants ambient, always-available intelligence that belongs entirely
to them.

---

## Why did you decide to build this, and why build it now?

Every AI tool available today makes the same implicit deal: you get
intelligence, they get your data, your keys, and a monthly fee. That deal is
getting worse as models get more capable. The more powerful the AI, the more
sensitive the actions it takes on your behalf — and the more dangerous it is
to route those actions through someone else's server.

We built Jarvis because that deal should not exist. Your private keys should
never leave your machine. Your trading strategy should not be readable by an
API provider. Your contracts, your conversations, your research — none of it
should be logged by a third party.

The timing is specific. Three things converged:

- **Local inference became viable.** Ollama runs capable models on a consumer
  laptop with no cloud required.
- **Solana matured.** You can now execute complex DeFi operations
  programmatically through Solana Agent Kit, Jupiter, and Pump.fun.
- **Hardware costs dropped.** The components needed for smart glasses — low-
  power ARM SoCs, lightweight displays, small cameras — fell to the point where
  an open-source reference design is buildable for a few hundred dollars.

The window where you can build a sovereign AI agent that is also a credible
product, rather than a prototype, opened recently. We decided to build through
it.

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
