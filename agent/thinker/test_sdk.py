"""Quick SDK connectivity test."""
import os
from dotenv import load_dotenv
load_dotenv()

# Must happen AFTER load_dotenv so we don't pass the direct API key to the subprocess
os.environ.pop("CLAUDECODE", None)
os.environ.pop("CLAUDE_CODE_ENTRYPOINT", None)
os.environ.pop("ANTHROPIC_API_KEY", None)  # Let claude CLI use stored auth

import asyncio
import sys

from claude_agent_sdk import query, ClaudeAgentOptions


async def main():
    count = 0
    async for msg in query(
        prompt="Reply with exactly one word: Hello",
        options=ClaudeAgentOptions(allowed_tools=[], debug_stderr=True),
    ):
        count += 1
        name = type(msg).__name__
        print(f"msg {count}: {name}", flush=True)
        if hasattr(msg, "result"):
            print("  result:", str(msg.result)[:300], flush=True)
        elif hasattr(msg, "content"):
            print("  content:", str(msg.content)[:300], flush=True)
    print(f"DONE — {count} messages total")


if __name__ == "__main__":
    asyncio.run(main())
