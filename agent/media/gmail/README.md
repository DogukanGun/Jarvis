# Gmail Webhook Bridge

Small Go service that receives the same Google Gmail Pub/Sub webhook as Inbox Zero, decodes the payload, and pushes events to a channel (and optionally streams them via SSE) so your agent can consume them as a tool.

## Behaviour

- **POST `/webhook`** (or `WEBHOOK_PATH`): Google Pub/Sub push endpoint.
  - Query param `token` must equal `GOOGLE_PUBSUB_VERIFICATION_TOKEN`.
  - Body: `{ "message": { "data": "<base64url>" } }` with decoded `{ "emailAddress", "historyId" }`.
  - Responds immediately with `200` and `{"ok":true}`, then pushes the decoded event to the internal channel.
- **GET `/events`**: Server-Sent Events stream. External agents can subscribe here; each Gmail push results in an `email` event with JSON `{ "emailAddress", "historyId", "receivedAt" }`.

## Setup

1. Copy `.env.example` to `.env` and set `GOOGLE_PUBSUB_VERIFICATION_TOKEN` to the same value you use when creating the Pub/Sub push subscription (e.g. Inbox Zero CLI or manual `gcloud`).
2. Create a push subscription that POSTs to `https://your-host/webhook?token=YOUR_TOKEN`.
3. Run the bridge (see below).

## Run

```bash
cd gmail-webhook-bridge
go run .
```

Or build and run:

```bash
go build -o gmail-webhook-bridge .
./gmail-webhook-bridge
```

## Env

| Variable | Description |
|----------|-------------|
| `GOOGLE_PUBSUB_VERIFICATION_TOKEN` | Required. Must match the `token` query param on webhook requests. |
| `PORT` | HTTP listen port (default `8080`). |
| `WEBHOOK_PATH` | Webhook path (default `/webhook`). |

## Using the channel in your agent (Go)

If your agent is in the same Go process, you can:

1. Build a library from this package that exposes the `events` channel and the webhook handler, or
2. Run this binary and have your agent subscribe to **GET /events** (SSE) and treat each `email` event as a tool input.

Example SSE client (e.g. from another process or language):

```bash
curl -N http://localhost:8080/events
```

Each line will be `event: email` followed by `data: {"emailAddress":"...","historyId":...,"receivedAt":"..."}`.
