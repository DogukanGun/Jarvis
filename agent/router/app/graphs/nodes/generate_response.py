"""Generate final response using LLM with memory context and tool results."""

from typing import Any, Dict
import json
import logging

from ..state import RouterGraphState

logger = logging.getLogger(__name__)

RESPONSE_SYSTEM_PROMPT = """You are Jarvis, an intelligent AI assistant. You help users with research, web browsing, and general conversation.

You have access to these capabilities:
- Memory: You remember past conversations and user preferences
- Thinker: A research pipeline that can produce academic papers on topics
- Web Fetcher: Can fetch and read web page content

Based on the context provided, generate a helpful and concise response."""


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

    context_str = "\n".join(context_parts) if context_parts else ""

    # Build the full prompt
    prompt = f"{RESPONSE_SYSTEM_PROMPT}\n\n{context_str}\n\nUser: {message}\n\nJarvis:"

    try:
        client = httpx.Client(timeout=60.0)
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
