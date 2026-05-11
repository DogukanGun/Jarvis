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

The desktop app is built with Electron, React 19, and TypeScript. The landing page uses Next.js 14 with Framer Motion for animations, deployed on Vercel. The backend is a mesh of ten microservices written in Python (Flask, FastAPI) and Node.js (Fastify), connected by Apache Kafka for real-time async event streaming between agents.

On the Solana side we integrate Solana Web3.js, SPL Token, and Solana Agent Kit v2 for on-chain execution, Jupiter for swap aggregation, and Pump.fun for token launches. Transaction signing runs through an isolated loopback HTTP server inside the Electron main process so private keys never touch the network.

For AI we run Ollama locally for LLM inference with no cloud dependency, OpenAI Whisper for voice input, YOLOv8 for real-time object detection in guard mode, and a custom RAG pipeline for legal document Q&A. Mem0 handles semantic memory across sessions. Claude Code was used as the primary AI coding assistant throughout development.

Infrastructure is Docker Compose running Kafka, Zookeeper, MinIO, and Ollama. Auth uses macOS Touch ID via Electron's native biometric API, AES-256 encrypted wallet vaults, and BIP39/Ed25519 key derivation.

