"""
LLM Client

Abstract client for LLM interactions with support for multiple providers.
"""

from typing import Dict, Any, Tuple, Optional
from abc import ABC, abstractmethod
import json


class LLMClient(ABC):
    """Abstract base class for LLM clients"""

    @abstractmethod
    def generate(self, context: Dict[str, Any]) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Generate response from LLM.

        Args:
            context: Context dict with persona, memory, task, user_prompt

        Returns:
            Tuple of (response_text, memory_intents)
        """
        pass


class MockLLMClient(LLMClient):
    """
    Mock LLM client for testing.

    Returns deterministic responses based on input.
    """

    def __init__(self, should_fail: bool = False, custom_response: Optional[str] = None):
        """
        Initialize mock client.

        Args:
            should_fail: If True, raises exception
            custom_response: Custom response to return
        """
        self.should_fail = should_fail
        self.custom_response = custom_response
        self.call_count = 0
        self.last_context = None

    def generate(self, context: Dict[str, Any]) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Generate mock response"""
        self.call_count += 1
        self.last_context = context

        if self.should_fail:
            raise Exception("Mock LLM error")

        if self.custom_response:
            response = self.custom_response
        else:
            # Generate deterministic response based on context
            user_prompt = context.get("user_prompt", "")
            task_type = context.get("task", {}).get("task_type", "unknown")

            response = f"Mock LLM response for task '{task_type}': {user_prompt}"

        # Generate minimal memory intents
        memory_intents = {
            "candidates": [],
            "signals": {
                "task_type": context.get("task", {}).get("task_type"),
                "app": context.get("task", {}).get("app"),
            }
        }

        return response, memory_intents


class OllamaLLMClient(LLMClient):
    """
    Ollama LLM client (local models like Llama3.1).

    Requires ollama to be running locally.
    """

    def __init__(self, model: str = "llama3.1", base_url: str = "http://localhost:11434", temperature: float = 0.7):
        """
        Initialize Ollama client.

        Args:
            model: Model name (e.g., llama3.1, llama2, mistral)
            base_url: Ollama API base URL
            temperature: Sampling temperature
        """
        self.model = model
        self.base_url = base_url
        self.temperature = temperature

        try:
            import httpx
            self.client = httpx.Client(timeout=120.0)
        except ImportError:
            raise ImportError("httpx package not installed. Install with: pip install httpx")

    def generate(self, context: Dict[str, Any]) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Generate response using Ollama"""
        # Build prompt
        system_prompt = self._build_system_prompt(context)
        user_prompt = self._build_prompt(context)

        # Call Ollama API
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": f"{system_prompt}\n\n{user_prompt}",
            "stream": False,
            "options": {
                "temperature": self.temperature
            }
        }

        try:
            response = self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            response_text = data.get("response", "")

            # Extract memory intents (basic version)
            memory_intents = {
                "candidates": [],
                "signals": {
                    "task_type": context.get("task", {}).get("task_type"),
                    "app": context.get("task", {}).get("app"),
                }
            }

            return response_text, memory_intents

        except Exception as e:
            raise Exception(f"Ollama API error: {str(e)}")

    def _build_system_prompt(self, context: Dict[str, Any]) -> str:
        """Build system prompt from persona"""
        persona = context.get("persona", {})
        name = persona.get("name", "Assistant")
        style_rules = persona.get("style_rules", [])

        system_prompt = f"You are {name}. "
        if style_rules:
            system_prompt += "Follow these rules:\n"
            for rule in style_rules:
                system_prompt += f"- {rule}\n"

        return system_prompt

    def _build_prompt(self, context: Dict[str, Any]) -> str:
        """Build user prompt from context"""
        parts = []

        # Add structured memory
        mem0_state = context.get("structured_memory", {})
        if mem0_state and mem0_state.get("items"):
            parts.append("Relevant memories:")
            for item in mem0_state["items"][:5]:
                text = item.get("text", item.get("memory", str(item)))
                parts.append(f"- {text}")
            parts.append("")

        # Add retrieved episodes
        episodes = context.get("retrieved_episodes", [])
        if episodes:
            parts.append("Related past interactions:")
            for ep in episodes[:3]:
                text = ep.get("text", str(ep))
                parts.append(f"- {text}")
            parts.append("")

        # Add task context
        task = context.get("task", {})
        if task:
            task_type = task.get("task_type")
            app = task.get("app")
            if task_type:
                parts.append(f"Task: {task_type}")
            if app:
                parts.append(f"App: {app}")
            parts.append("")

        # Add user prompt
        user_prompt = context.get("user_prompt", "")
        parts.append("User request:")
        parts.append(user_prompt)

        return "\n".join(parts)


class OpenAILLMClient(LLMClient):
    """
    OpenAI LLM client (GPT models).

    Requires openai package to be installed.
    """

    def __init__(self, api_key: str, model: str = "gpt-4", temperature: float = 0.7, max_tokens: int = 2000):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key
            model: Model name (e.g., gpt-4, gpt-3.5-turbo)
            temperature: Sampling temperature
            max_tokens: Max tokens in response
        """
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        try:
            import openai
            self.client = openai.OpenAI(api_key=api_key)
        except ImportError:
            raise ImportError("openai package not installed. Install with: pip install openai")

    def generate(self, context: Dict[str, Any]) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Generate response using OpenAI"""
        # Convert context to prompt
        prompt = self._build_prompt(context)

        # Call OpenAI API
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self._build_system_prompt(context)},
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )

        response_text = response.choices[0].message.content

        # Extract memory intents (basic version)
        memory_intents = {
            "candidates": [],
            "signals": {
                "task_type": context.get("task", {}).get("task_type"),
                "app": context.get("task", {}).get("app"),
            }
        }

        return response_text, memory_intents

    def _build_system_prompt(self, context: Dict[str, Any]) -> str:
        """Build system prompt from persona"""
        persona = context.get("persona", {})
        name = persona.get("name", "Assistant")
        style_rules = persona.get("style_rules", [])

        system_prompt = f"You are {name}. "
        if style_rules:
            system_prompt += "Follow these rules:\n"
            for rule in style_rules:
                system_prompt += f"- {rule}\n"

        return system_prompt

    def _build_prompt(self, context: Dict[str, Any]) -> str:
        """Build user prompt from context"""
        parts = []

        # Add structured memory
        mem0_state = context.get("structured_memory", {})
        if mem0_state and mem0_state.get("items"):
            parts.append("Relevant memories:")
            for item in mem0_state["items"][:5]:
                text = item.get("text", item.get("memory", str(item)))
                parts.append(f"- {text}")
            parts.append("")

        # Add retrieved episodes
        episodes = context.get("retrieved_episodes", [])
        if episodes:
            parts.append("Related past interactions:")
            for ep in episodes[:3]:
                if isinstance(ep, dict) and "episode" in ep:
                    ep_data = ep["episode"]
                else:
                    ep_data = ep
                text = ep_data.get("text", str(ep_data))
                parts.append(f"- {text}")
            parts.append("")

        # Add task context
        task = context.get("task", {})
        if task:
            task_type = task.get("task_type")
            app = task.get("app")
            if task_type:
                parts.append(f"Task: {task_type}")
            if app:
                parts.append(f"App: {app}")
            parts.append("")

        # Add user prompt
        user_prompt = context.get("user_prompt", "")
        parts.append("User request:")
        parts.append(user_prompt)

        return "\n".join(parts)


# Factory function
def get_llm_client(
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs
) -> LLMClient:
    """
    Factory function to get LLM client.

    Args:
        provider: Provider name (ollama, openai, mock)
        api_key: API key (optional, uses config default)
        model: Model name (optional, uses config default)
        **kwargs: Additional provider-specific args

    Returns:
        LLMClient instance
    """
    from app.config import config

    provider = provider or config.LLM_PROVIDER
    api_key = api_key or config.LLM_API_KEY
    model = model or config.LLM_MODEL

    if provider == "mock":
        return MockLLMClient(**kwargs)
    elif provider == "ollama":
        base_url = kwargs.get("base_url", config.OLLAMA_BASE_URL)
        temperature = kwargs.get("temperature", config.LLM_TEMPERATURE)
        return OllamaLLMClient(
            model=model,
            base_url=base_url,
            temperature=temperature
        )
    elif provider == "openai":
        temperature = kwargs.get("temperature", config.LLM_TEMPERATURE)
        max_tokens = kwargs.get("max_tokens", config.LLM_MAX_TOKENS)
        return OpenAILLMClient(
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
