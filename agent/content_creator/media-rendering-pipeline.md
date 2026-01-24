# Media Rendering Pipeline (Kafka-based)

## Project overview

We are adding a **Media Rendering Pipeline** to our existing Kafka-based microservice ecosystem.  
The goal is simple: **any service** can publish a rendering request (text/prompt + type + optional image input), and receive back a **publicly accessible URL** to the generated media (image or video).

Kafka stays the external contract between services. The pipeline is implemented as **five dedicated services**, each responsible for a single media capability. A router service dispatches requests to the correct generator/editor based on request type and payload fields.

---

## Key principles

- **Kafka-first integration**: No change to the global architecture; all interaction happens through Kafka topics.
- **Separation of concerns**: Routing is isolated from generation/editing.
- **Scalable by workload**: Video and image workloads are separated so they can scale independently (e.g., GPU nodes for video).
- **Uniform output contract**: Every request results in a message containing `success` and an optional `response_url`.

---

## Message flow (high level)

1. A producer service publishes a request to a single “entry” topic.
2. **Content Router** consumes the request and routes it to exactly one specialized service topic.
3. The selected generator/editor produces the media, uploads it to object storage, and publishes the result to the results topic.
4. The original producer (or any interested consumer) listens for the result and uses the returned URL.

---

## Common message contracts

### Request (recommended)

All requests share the same envelope; different services require different fields.

```json
{
  "job_id": "uuid",
  "task": "video_from_prompt | image_from_prompt | image_from_prompt_and_image | edit_image_from_prompt_and_image",
  "prompt": "string",
  "input_image_url": "string (optional)",
  "output": { "format": "mp4|png|jpg", "width": 1024, "height": 1024, "duration_s": 6 },
  "meta": { "style": "optional", "seed": 123 }
}
```

### Result

```json
{
  "job_id": "uuid",
  "success": true,
  "response_url": "https://...",
  "error": "string | null"
}
```

> Note: Even if you keep a minimal schema internally, having `job_id` is strongly recommended for correlation, observability, and safe retries.

---

## Services (5 total)

### 1) Content Router (Dispatcher)

**Responsibility:** Single entry point that routes work to the correct downstream service.

- Consumes: `media.render.requests`
- Produces: one of the downstream topics based on `task` + presence of `input_image_url`

Routing rules example:
- `task = video_from_prompt` → Video Generator
- `task = image_from_prompt` → Image Generator (prompt-only)
- `task = image_from_prompt_and_image` → Image Generator (prompt + existing image)
- `task = edit_image_from_prompt_and_image` → Image Editor

This service is intentionally “thin”: it does not generate media, it only validates/routes.

---

### 2) Video Generator (Content Generator)

**Responsibility:** Generate a video using prompt-only input.

- Input: `prompt`, optional output settings (`duration_s`, resolution, format)
- Output: uploaded video URL
- Consumes: `media.render.video.requests`
- Produces: `media.render.results`

Typical usage:
- “Create a 6s cinematic clip of a futuristic Munich street at night…”

---

### 3) Image Generator (Prompt-only Content Generator)

**Responsibility:** Generate an image purely from a text prompt.

- Input: `prompt`, output settings (size/format)
- Output: uploaded image URL
- Consumes: `media.render.image.prompt.requests`
- Produces: `media.render.results`

Typical usage:
- “Generate a clean product-style image of …”

---

### 4) Image Generator (Prompt + Existing Image)

**Responsibility:** Generate an image while using an existing image as a reference (e.g., style reference, composition reference, or image-to-image variation depending on model choice).

- Input: `prompt` + `input_image_url`
- Output: uploaded image URL
- Consumes: `media.render.image.reference.requests`
- Produces: `media.render.results`

Typical usage:
- “Use this photo as a reference, generate the same scene in anime style…”

---

### 5) Image Editor (Image + Prompt)

**Responsibility:** Edit/transform an existing image based on a prompt (inpainting/outpainting, object removal, background change, color correction, etc.).

- Input: `input_image_url` + `prompt`
- Output: uploaded edited image URL
- Consumes: `media.render.image.edit.requests`
- Produces: `media.render.results`

Typical usage:
- “Remove the background and replace it with a white studio backdrop…”

---

## Kafka topics (suggested)

Entry:
- `media.render.requests`

Routed topics:
- `media.render.video.requests`
- `media.render.image.prompt.requests`
- `media.render.image.reference.requests`
- `media.render.image.edit.requests`

Results:
- `media.render.results`

(You said you don’t need a DLQ, so we skip it.)

---

## Storage + URL output

Each generator/editor uploads the produced media to a shared storage layer (e.g., S3/R2/GCS/MinIO).  
The `response_url` in the results topic points to the uploaded asset (CDN URL or signed URL depending on your setup).

---

## What this enables

- Any service can request media generation with **one Kafka publish**
- Workloads scale independently (video vs image vs edit)
- New capabilities are added by introducing new “generator/editor” services + a router rule
- No changes required to the overall system architecture beyond adding these services and topics
