import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Type, TypeVar

import httpx
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import config

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        json_mode: bool = False,
    ) -> str: ...

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system: str = "",
        temperature: float = 0.3,
    ) -> T:
        """Generate structured output parsed into a Pydantic model.

        Default implementation: call generate with json_mode and parse.
        Subclasses can override for native structured output support.
        """
        raw = await self.generate(prompt, system=system, temperature=temperature, json_mode=True)
        return response_model.model_validate_json(raw)


class OllamaClient(LLMClient):
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        json_mode: bool = False,
    ) -> str:
        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if json_mode:
            payload["format"] = "json"

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["response"]


class OpenAIClient(LLMClient):
    def __init__(self, api_key: str, model: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        json_mode: bool = False,
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = await self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system: str = "",
        temperature: float = 0.3,
    ) -> T:
        """Use OpenAI's native structured output (response_format with json_schema)."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.beta.chat.completions.parse(
            model=self.model,
            messages=messages,
            temperature=temperature,
            response_format=response_model,
        )
        return response.choices[0].message.parsed


class AnthropicClient(LLMClient):
    def __init__(self, api_key: str, model: str):
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

    async def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        json_mode: bool = False,
    ) -> str:
        kwargs: dict = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system

        response = await self.client.messages.create(**kwargs)
        return response.content[0].text


class ClaudeCodeClient(LLMClient):
    def __init__(self, claude_path: str = "claude"):
        self.claude_path = claude_path

    async def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        json_mode: bool = False,
    ) -> str:
        full_prompt = prompt
        if system:
            full_prompt = f"{system}\n\n{prompt}"

        process = await asyncio.create_subprocess_exec(
            self.claude_path,
            "-p",
            full_prompt,
            "--output-format",
            "json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(
                "Claude Code CLI failed (exit %d): %s",
                process.returncode,
                stderr.decode().strip(),
            )

        raw_output = stdout.decode().strip()

        try:
            parsed = json.loads(raw_output)
            # Claude Code JSON output contains a "result" field with the text
            if isinstance(parsed, dict):
                return parsed.get("result", parsed.get("text", raw_output))
            return raw_output
        except (json.JSONDecodeError, KeyError):
            logger.debug("Failed to parse Claude Code JSON output, returning raw stdout")
            return raw_output


def create_llm_client(provider: str = None) -> LLMClient:
    provider = provider or config.LLM_PROVIDER

    if provider == "ollama":
        return OllamaClient(config.OLLAMA_BASE_URL, config.LLM_MODEL)
    elif provider == "openai":
        return OpenAIClient(config.OPENAI_API_KEY, config.OPENAI_MODEL)
    elif provider == "anthropic":
        return AnthropicClient(config.ANTHROPIC_API_KEY, config.ANTHROPIC_MODEL)
    elif provider == "claude-code":
        return ClaudeCodeClient(config.CLAUDE_CODE_PATH)
    else:
        logger.warning("Unknown LLM provider '%s', falling back to ollama", provider)
        return OllamaClient(config.OLLAMA_BASE_URL, config.LLM_MODEL)
