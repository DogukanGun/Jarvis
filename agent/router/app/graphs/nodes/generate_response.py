"""Generate final response using LLM with memory context and tool results."""

from typing import Any, Dict
import json
import logging

from ..state import RouterGraphState

logger = logging.getLogger(__name__)

RESPONSE_SYSTEM_PROMPT = """You are Jarvis, an intelligent AI assistant. You help users with research, web browsing, and general conversation.

CRITICAL RULES:
- If "## Tool results:" contains "Fetched page:", the web page has ALREADY been fetched and its content is right there. Summarize or answer from it. NEVER say you cannot browse the web.
- If tool results mention a research pipeline started, confirm it is running.
- For general questions, give a direct helpful answer.

Be concise and focused on what the user asked.

EMOTIONAL AWARENESS:
- If emotion context is provided, subtly adapt your tone to match the user's emotional state.
- For negative emotions (sad, angry, frustrated, anxious), be empathetic and supportive.
- For positive emotions (happy, excited, grateful), mirror the energy warmly.
- For curious users, be thorough and engaging.
- For confused users, be extra clear and structured.
- Never explicitly mention that you detected their emotion.

VISUAL AWARENESS:
- If visual context is provided, you can see what the user sees through their camera.
- Reference detected objects naturally when relevant to the conversation.
- Do not list objects unprompted unless the user asks what you see."""


def generate_response(state: RouterGraphState) -> Dict[str, Any]:
    """Generate the final response using LLM."""
    from app.config import config
    import httpx

    message = state.get("message", "")
    intent = state.get("intent", "chat")
    tool_results = state.get("tool_results", {})
    memory_episodes = state.get("memory_episodes", [])
    conversation_history = state.get("conversation_history", [])

    # Build context prompt
    context_parts = []

    # Add memory context
    if memory_episodes:
        context_parts.append("## Relevant memories:")
        for ep in memory_episodes[:5]:
            text = ep.get("text", ep.get("content", ""))
            if text:
                context_parts.append(f"- {text[:200]}")

    # Add conversation history
    if conversation_history:
        context_parts.append("\n## Recent conversation:")
        for msg in conversation_history[-6:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")[:300]
            context_parts.append(f"{role}: {content}")

    # Add tool results
    if tool_results:
        context_parts.append("\n## Tool results:")
        for tool_name, result in tool_results.items():
            if tool_name == "thinker":
                if result.get("status") == "started":
                    context_parts.append(
                        f"Research pipeline started for topic: {result.get('topic')}. "
                        f"User can track progress at {result.get('monitor_url', 'the thinker monitor')}."
                    )
                elif result.get("error"):
                    context_parts.append(f"Thinker error: {result['error']}")
            elif tool_name == "web_fetcher":
                if result.get("error"):
                    context_parts.append(f"Web fetch error: {result['error']}")
                else:
                    context_parts.append(
                        f"Fetched page: {result.get('title', 'Unknown')}\n"
                        f"Content:\n{result.get('content', '')[:3000]}"
                    )
            elif tool_name == "swiss_knife":
                if result.get("error"):
                    context_parts.append(f"Security tool error: {result['error']}")
                elif result.get("status") == "confirmation_required":
                    context_parts.append(
                        f"Security tool requires confirmation before execution.\n"
                        f"Prompt: {result.get('confirmation_prompt', '')}\n"
                        f"Job ID: {result.get('job_id', '')}"
                    )
                else:
                    sk_response = result.get("response", "")
                    sk_tools = result.get("tools_used", [])
                    sk_findings = result.get("findings", [])
                    context_parts.append(f"Security tools executed: {', '.join(sk_tools) if sk_tools else 'none'}")
                    if sk_response:
                        context_parts.append(f"Result: {sk_response[:3000]}")
                    if sk_findings:
                        context_parts.append("Findings:")
                        for f in sk_findings[:10]:
                            context_parts.append(f"  - {json.dumps(f, default=str)[:200]}")

    # Add emotion context if confidence is meaningful
    emotion_analysis = state.get("emotion_analysis", {})
    if emotion_analysis.get("confidence", 0.0) > 0.3:
        emotion = emotion_analysis.get("emotion", "neutral")
        valence = emotion_analysis.get("valence", 0.0)
        arousal = emotion_analysis.get("arousal", 0.3)
        context_parts.append(
            f"\n## Emotion context:\n"
            f"Detected emotion: {emotion} (valence={valence:.1f}, arousal={arousal:.1f})"
        )

    visual_context = state.get("visual_context")
    if visual_context and visual_context.get("summary"):
        context_parts.append(
            f"\n## Visual context (camera):\n"
            f"Objects detected: {visual_context['summary']}"
        )

    # For web_fetch: summarize the fetched content with a focused LLM prompt
    wf_result = tool_results.get("web_fetcher", {})
    if intent == "web_fetch" and wf_result:
        if wf_result.get("error"):
            return {"response": f"Could not fetch the page: {wf_result['error']}"}
        content = wf_result.get("content", "")
        title = wf_result.get("title", "")
        url = wf_result.get("url", "")
        if content:
            try:
                client = httpx.Client(timeout=60.0)
                summarize_prompt = (
                    f"The user asked: {message}\n\n"
                    f"Here is the content fetched from {url}:\n"
                    f"Title: {title}\n\n"
                    f"{content[:4000]}\n\n"
                    f"Summarize the key information from this page that answers the user's question. "
                    f"Be concise and clear."
                )
                if config.LLM_PROVIDER == "openai":
                    resp = client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
                        json={
                            "model": config.LLM_MODEL,
                            "messages": [{"role": "user", "content": summarize_prompt}],
                            "temperature": 0.3,
                        },
                    )
                    resp.raise_for_status()
                    summary = resp.json()["choices"][0]["message"]["content"].strip()
                else:
                    resp = client.post(
                        f"{config.OLLAMA_BASE_URL}/api/generate",
                        json={"model": config.LLM_MODEL, "prompt": summarize_prompt, "stream": False},
                    )
                    resp.raise_for_status()
                    summary = resp.json().get("response", "").strip()
                client.close()
                if summary:
                    return {"response": summary}
            except Exception as e:
                logger.error(f"Web fetch summarization failed: {e}")
                # Fall through to raw content
            header = f"**{title}** ({url})\n\n" if title else f"**{url}**\n\n"
            return {"response": header + content[:3000]}

    # For security tool: pass through completed response or return async status
    sk_result = tool_results.get("swiss_knife", {})
    if intent == "security" and sk_result:
        if sk_result.get("status") == "started":
            job_id = sk_result.get("job_id", "")
            monitor_url = sk_result.get("monitor_url", "http://localhost:3003")
            return {
                "response": (
                    f"Security scan started! Your scan is now running in the background.\n\n"
                    f"**Job ID:** `{job_id[:8]}...`\n\n"
                    f"Track progress in real-time at the "
                    f"[Swiss Army Knife Monitor]({monitor_url})\n\n"
                    f"The scan will execute network tools, analyze results, "
                    f"and generate a full security report."
                )
            }
        if sk_result.get("response") and not sk_result.get("error"):
            # Merge the sub-agent's detailed tool names into tools_used
            sub_tools = sk_result.get("tools_used", [])
            current_tools = state.get("tools_used", [])
            merged_tools = current_tools + [t for t in sub_tools if t not in current_tools]
            return {
                "response": sk_result["response"],
                "tools_used": merged_tools,
                "findings": sk_result.get("findings", []),
                "report": sk_result.get("report", {}),
            }

    context_str = "\n".join(context_parts) if context_parts else ""

    # Build the full prompt
    prompt = f"{RESPONSE_SYSTEM_PROMPT}\n\n{context_str}\n\nUser: {message}\n\nJarvis:"

    try:
        client = httpx.Client(timeout=60.0)
        if config.LLM_PROVIDER == "openai":
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
                json={
                    "model": config.LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": RESPONSE_SYSTEM_PROMPT},
                        {"role": "user", "content": f"{context_str}\n\nUser: {message}"},
                    ],
                    "temperature": config.LLM_TEMPERATURE,
                },
            )
            resp.raise_for_status()
            response_text = resp.json()["choices"][0]["message"]["content"].strip()
        else:
            resp = client.post(
                f"{config.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": config.LLM_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": config.LLM_TEMPERATURE},
                },
            )
            resp.raise_for_status()
            response_text = resp.json().get("response", "").strip()
        client.close()

        if not response_text:
            response_text = "I'm sorry, I couldn't generate a response. Please try again."

        return {"response": response_text}

    except Exception as e:
        logger.error(f"Response generation failed: {e}")

        # Provide a fallback response based on tool results
        if tool_results.get("thinker", {}).get("status") == "started":
            return {
                "response": (
                    f"I've started a research pipeline on the topic. "
                    f"You can track its progress at http://localhost:3000"
                )
            }
        if tool_results.get("web_fetcher", {}).get("content"):
            return {
                "response": (
                    f"Here's what I found from {tool_results['web_fetcher'].get('title', 'the page')}:\n\n"
                    f"{tool_results['web_fetcher']['content'][:2000]}"
                )
            }

        return {"response": f"I encountered an error generating a response: {e}"}
