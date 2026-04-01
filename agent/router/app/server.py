"""
Router Agent FastAPI Server

Central orchestrator that routes user messages to sub-agents
(thinker, web_fetcher, swiss_army_knife) with memory integration.

On startup a background Kafka consumer thread is started (if enabled via
ENABLE_KAFKA_CONSUMER).  When sub-agents publish task lifecycle events to
Kafka, the consumer picks them up and broadcasts them to all active WebSocket
clients so the UI can react in real-time without polling.
"""

import asyncio
import json
import logging
import threading
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Set

from fastapi import FastAPI, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import config
from app.models import AgentStatus, ChatRequest, ChatResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Active WebSocket client registry
# ---------------------------------------------------------------------------

_ws_clients: Set[WebSocket] = set()
_ws_lock = asyncio.Lock()


async def broadcast_to_ws_clients(event: Dict[str, Any]) -> None:
    """Send an event dict to every connected WebSocket client.

    Dead connections are silently removed from the registry.
    """
    dead: Set[WebSocket] = set()
    async with _ws_lock:
        clients = list(_ws_clients)

    for ws in clients:
        try:
            await ws.send_json(event)
        except Exception:
            dead.add(ws)

    if dead:
        async with _ws_lock:
            _ws_clients.difference_update(dead)


# ---------------------------------------------------------------------------
# Kafka consumer startup / shutdown (lifespan)
# ---------------------------------------------------------------------------

_kafka_thread: threading.Thread | None = None
_kafka_consumer = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan: start Kafka consumer on startup, stop on shutdown."""
    global _kafka_thread, _kafka_consumer

    # Register security notification channels
    from app.security.event_bus import event_bus
    from app.security.channels.websocket import WebSocketChannel
    from app.security.channels.telegram import TelegramChannel
    from app.security.channels.email import EmailChannel

    event_bus.register(WebSocketChannel(_ws_clients))
    event_bus.register(TelegramChannel(config))
    event_bus.register(EmailChannel(config))

    if config.ENABLE_KAFKA_CONSUMER:
        loop = asyncio.get_event_loop()
        try:
            from app.kafka.consumer import RouterKafkaConsumer

            _kafka_consumer = RouterKafkaConsumer(
                broadcast_callback=broadcast_to_ws_clients,
                loop=loop,
            )
            _kafka_thread = threading.Thread(
                target=_kafka_consumer.start,
                daemon=True,
                name="router-kafka-consumer",
            )
            _kafka_thread.start()
            logger.info("Router Kafka consumer started in background thread")
        except Exception as exc:
            logger.warning("Could not start Kafka consumer: %s", exc)
    else:
        logger.info("Kafka consumer disabled (ENABLE_KAFKA_CONSUMER=false)")

    yield

    if _kafka_consumer is not None:
        _kafka_consumer.close()
        logger.info("Router Kafka consumer stopped")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Jarvis Router",
    description="Central orchestrator for Jarvis AI agents",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory conversation store (per user_id)
_conversations: Dict[str, List[Dict[str, str]]] = {}


# ---------------------------------------------------------------------------
# HTTP chat endpoint
# ---------------------------------------------------------------------------

@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Process a user message through the router graph.

    1. Retrieves memory context
    2. Classifies intent (chat / research / web_fetch / security)
    3. Invokes appropriate sub-agent
    4. Generates response
    5. Writes to memory
    """
    from app.graphs.router_graph import run_router
    from app.graphs.nodes import analyze_emotion

    history = _conversations.get(req.user_id, [])

    t0 = time.time()
    result = run_router(
        user_id=req.user_id,
        message=req.message,
        conversation_history=history,
    )
    duration_ms = round((time.time() - t0) * 1000)

    # Run emotion analysis on the message (first iteration: after graph completes)
    emotion_result = analyze_emotion({"user_id": req.user_id, "message": req.message})
    emotion = emotion_result.get("emotion_analysis", {})

    response_text = result.get("response", "Sorry, I couldn't process that.")
    intent = result.get("intent", "chat")
    tools_used = result.get("tools_used", [])
    findings = result.get("findings", [])
    report = result.get("report", {})

    history.append({"role": "user", "content": req.message})
    history.append({"role": "assistant", "content": response_text})
    _conversations[req.user_id] = history[-20:]

    return ChatResponse(
        response=response_text,
        intent=intent,
        tools_used=tools_used,
        findings=findings,
        report=report,
        metadata={
            "duration_ms": duration_ms,
            "user_id": req.user_id,
            "emotion": emotion,
        },
    )


# ---------------------------------------------------------------------------
# WebSocket chat endpoint
# ---------------------------------------------------------------------------

@app.websocket("/ws/chat")
async def ws_chat(ws: WebSocket):
    """WebSocket chat endpoint — streams status updates and final response.

    The connection is also registered so that Kafka-sourced agent events
    (task.completed, result.security_scan, etc.) are pushed to the client
    in real-time without any additional polling.
    """
    await ws.accept()
    async with _ws_lock:
        _ws_clients.add(ws)
    logger.info("WebSocket client connected (%d total)", len(_ws_clients))

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            user_id = data.get("user_id", "default")
            message = data.get("message", "")
            intent_hint = data.get("intent")  # CLI can force intent to skip LLM classification
            visual_frame = data.get("visual_frame")
            visual_feed = None
            if visual_frame:
                visual_feed = {"source": "desktop", "way": "yolo", "data": {"frame_b64": visual_frame}}

            if not message:
                await ws.send_json({"type": "error", "content": "Empty message"})
                continue

            # Guard mode alarm trigger — short-circuit before the LLM graph
            if message.strip() == "/trigger":
                from app.security.event_bus import event_bus, SecurityEvent
                event = SecurityEvent(type="alarm_triggered", message="Manual alarm triggered by user")
                await event_bus.broadcast(event)
                await ws.send_json({"type": "response", "content": "Alarm triggered."})
                continue

            history = _conversations.get(user_id, [])

            await ws.send_json({"type": "status", "content": "Classifying intent..."})

            t0 = time.time()

            # ----------------------------------------------------------
            # Run the graph in a thread but split intent classification
            # from tool execution so we can send status updates in between.
            # ----------------------------------------------------------
            from app.graphs.router_graph import router_graph as _router_graph

            _VALID_INTENTS = {"chat", "research", "web_fetch", "security"}
            initial_state = {
                "user_id": user_id,
                "message": message,
                "conversation_history": history,
                "tools_used": [],
                "tool_results": {},
                "visual_feed": visual_feed,
                # Pre-set intent if client provided a valid hint (bypasses LLM classification)
                **({"intent": intent_hint} if intent_hint in _VALID_INTENTS else {}),
            }

            # ------------------------------------------------------------------
            # Phase 1: pre-classify — memory retrieval, emotion, visual run
            # IN PARALLEL via a thread pool so no step blocks another.
            # analyze_emotion is now rule-based (instant); retrieve_memory is
            # the only real I/O here (~1-2s).
            # ------------------------------------------------------------------
            from concurrent.futures import ThreadPoolExecutor
            from app.graphs.nodes import retrieve_memory, classify_intent as _classify, analyze_emotion, process_visual

            def _classify_phase(s):
                # Fan out: retrieve memory, analyse emotion, process visual — all at once
                with ThreadPoolExecutor(max_workers=3) as pool:
                    mem_fut = pool.submit(retrieve_memory, s)
                    emo_fut = pool.submit(analyze_emotion, s)
                    vis_fut = pool.submit(process_visual, s)
                    mem_r = mem_fut.result()
                    emo_r = emo_fut.result()
                    vis_r = vis_fut.result()

                merged = {**s, **mem_r, **emo_r, **vis_r}
                # classify_intent short-circuits when intent is pre-set
                classified = {**merged, **_classify(merged)}
                return classified

            phase1 = await asyncio.to_thread(_classify_phase, initial_state)
            intent_detected = phase1.get("intent", "chat")

            # Send the detected intent as a status update
            _INTENT_LABELS = {
                "chat": "Generating response...",
                "research": "Starting research pipeline...",
                "web_fetch": "Fetching web content...",
                "security": "Executing security tools (this may take a moment)...",
            }
            await ws.send_json({
                "type": "status",
                "content": _INTENT_LABELS.get(intent_detected, "Processing..."),
            })

            # ------------------------------------------------------------------
            # Phase 2: run the full graph.
            # retrieve_memory and classify_intent short-circuit (already done).
            # write_memory is fired in the background so it doesn't delay the
            # WebSocket response to the client.
            # ------------------------------------------------------------------
            def _generate_phase(s):
                from app.graphs.router_graph import router_graph as _g
                return _g.invoke(s)

            result = await asyncio.to_thread(_generate_phase, phase1)

            duration_ms = round((time.time() - t0) * 1000)

            response_text = result.get("response", "Sorry, I couldn't process that.")
            intent = result.get("intent", "chat")
            tools_used = result.get("tools_used", [])
            findings = result.get("findings", [])
            report = result.get("report", {})

            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": response_text})
            _conversations[user_id] = history[-20:]

            await ws.send_json({
                "type": "response",
                "content": response_text,
                "intent": intent,
                "tools_used": tools_used,
                "findings": findings,
                "report": report,
                "emotion": result.get("emotion_analysis", {}),
                "visual_context": result.get("visual_context", {}),
                "duration_ms": duration_ms,
            })

            # Fire-and-forget: persist exchange to memory without blocking client
            from app.graphs.nodes import write_memory as _write_memory
            mem_state = {**phase1, "response": response_text}
            asyncio.create_task(asyncio.to_thread(_write_memory, mem_state))


    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as exc:
        logger.error("WebSocket error: %s", exc)
        try:
            await ws.send_json({"type": "error", "content": str(exc)})
        except Exception:
            pass
    finally:
        async with _ws_lock:
            _ws_clients.discard(ws)
        logger.info("WebSocket client removed (%d remaining)", len(_ws_clients))


# ---------------------------------------------------------------------------
# Security alert endpoint
# ---------------------------------------------------------------------------

from pydantic import BaseModel


class SecurityAlertRequest(BaseModel):
    image_b64: str
    message: str = "Intruder detected!"


@app.post("/api/security/alert")
async def security_alert(req: SecurityAlertRequest):
    """Receive a security alert from the desktop guard mode.

    Broadcasts a SecurityEvent to all registered channels (WebSocket, Telegram,
    email, etc.) concurrently. Channels that are not configured are silently skipped.
    """
    from app.security.event_bus import event_bus, SecurityEvent

    event = SecurityEvent(
        type="intruder_detected",
        message=req.message,
        image_b64=req.image_b64,
    )
    await event_bus.broadcast(event)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Speech-to-text endpoint
# ---------------------------------------------------------------------------

@app.post("/api/transcribe")
async def transcribe(file: UploadFile):
    """Transcribe audio to text using OpenAI Whisper."""
    import httpx

    audio_bytes = await file.read()
    if not audio_bytes:
        return {"text": "", "error": "Empty audio"}

    try:
        client = httpx.Client(timeout=30.0)
        resp = client.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
            files={"file": (file.filename or "audio.webm", audio_bytes, file.content_type or "audio/webm")},
            data={"model": "whisper-1"},
        )
        resp.raise_for_status()
        client.close()
        text = resp.json().get("text", "").strip()
        return {"text": text}
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return {"text": "", "error": str(e)}


# ---------------------------------------------------------------------------
# Health / status endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    """Health check with sub-agent connectivity."""
    return {
        "status": "ok",
        "service": "jarvis-router",
        "port": config.ROUTER_PORT,
        "ws_clients": len(_ws_clients),
        "kafka_consumer": _kafka_thread.is_alive() if _kafka_thread else False,
    }


@app.get("/api/agents/status")
async def agents_status():
    """Check health of all connected sub-agents."""
    from app.clients.thinker_client import ThinkerClient
    from app.clients.web_fetcher_client import WebFetcherClient
    from app.clients.memory_client import MemoryClient
    from app.clients.swiss_knife_client import SwissKnifeClient
    from app.clients.vision_client import VisionClient

    agents = []

    tc = ThinkerClient()
    agents.append(AgentStatus(name="thinker", url=config.THINKER_BASE_URL, healthy=tc.health_check()))
    tc.close()

    wf = WebFetcherClient()
    agents.append(AgentStatus(name="web_fetcher", url=config.WEB_FETCHER_BASE_URL, healthy=wf.health_check()))
    wf.close()

    mc = MemoryClient()
    agents.append(AgentStatus(name="memory", url=config.MEMORY_BASE_URL, healthy=mc.health_check()))
    mc.close()

    sk = SwissKnifeClient()
    agents.append(AgentStatus(name="swiss_army_knife", url=config.SWISS_KNIFE_BASE_URL, healthy=sk.health_check()))
    sk.close()

    vc = VisionClient()
    agents.append(AgentStatus(name="vision", url=config.VISION_BASE_URL, healthy=vc.health_check()))
    vc.close()

    return {"agents": [a.model_dump() for a in agents]}
