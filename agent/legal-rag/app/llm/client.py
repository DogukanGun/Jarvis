"""Configurable LLM client: Anthropic (Claude) or OpenAI."""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from app.config import config

logger = logging.getLogger(__name__)


class LegalLLMClient:
    def __init__(self) -> None:
        self._provider = config.LLM_PROVIDER
        if self._provider == "anthropic":
            import anthropic  # type: ignore
            self._anthropic = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
            self._model = config.ANTHROPIC_MODEL
        else:
            import openai  # type: ignore
            self._openai = openai.OpenAI(api_key=config.OPENAI_API_KEY)
            self._model = config.OPENAI_MODEL

    async def generate(self, system: str, user: str) -> str:
        """Non-streaming generation. Returns the full response string."""
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._generate_sync, system, user)

    def _generate_sync(self, system: str, user: str) -> str:
        try:
            if self._provider == "anthropic":
                resp = self._anthropic.messages.create(
                    model=self._model,
                    max_tokens=2048,
                    temperature=config.LLM_TEMPERATURE,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
                return resp.content[0].text
            else:
                resp = self._openai.chat.completions.create(
                    model=self._model,
                    temperature=config.LLM_TEMPERATURE,
                    max_tokens=2048,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                )
                return resp.choices[0].message.content or ""
        except Exception as e:
            logger.error("LLM generate error: %s", e)
            raise

    async def generate_stream(self, system: str, user: str) -> AsyncGenerator[str, None]:
        """Streaming generation — yields text chunks."""
        if self._provider == "anthropic":
            async for chunk in self._stream_anthropic(system, user):
                yield chunk
        else:
            async for chunk in self._stream_openai(system, user):
                yield chunk

    async def _stream_anthropic(self, system: str, user: str) -> AsyncGenerator[str, None]:
        import asyncio

        # Anthropic streaming is sync; run in executor and yield chunks via a queue
        import queue as _queue
        q: _queue.Queue = _queue.Queue()
        sentinel = object()

        def _run() -> None:
            try:
                with self._anthropic.messages.stream(
                    model=self._model,
                    max_tokens=2048,
                    temperature=config.LLM_TEMPERATURE,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                ) as stream:
                    for text in stream.text_stream:
                        q.put(text)
            except Exception as e:
                q.put(e)
            finally:
                q.put(sentinel)

        loop = asyncio.get_event_loop()
        fut = loop.run_in_executor(None, _run)

        while True:
            item = await loop.run_in_executor(None, q.get)
            if item is sentinel:
                break
            if isinstance(item, Exception):
                raise item
            yield item

        await fut

    async def _stream_openai(self, system: str, user: str) -> AsyncGenerator[str, None]:
        import asyncio

        import queue as _queue
        q: _queue.Queue = _queue.Queue()
        sentinel = object()

        def _run() -> None:
            try:
                stream = self._openai.chat.completions.create(
                    model=self._model,
                    temperature=config.LLM_TEMPERATURE,
                    max_tokens=2048,
                    stream=True,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        q.put(delta)
            except Exception as e:
                q.put(e)
            finally:
                q.put(sentinel)

        loop = asyncio.get_event_loop()
        fut = loop.run_in_executor(None, _run)

        while True:
            item = await loop.run_in_executor(None, q.get)
            if item is sentinel:
                break
            if isinstance(item, Exception):
                raise item
            yield item

        await fut

    async def extract_json(self, system: str, user: str) -> str:
        """Generate a response expected to be raw JSON (no markdown fences)."""
        system_with_json = system + "\n\nRESPOND WITH VALID JSON ONLY. No markdown, no explanation."
        return await self.generate(system_with_json, user)
