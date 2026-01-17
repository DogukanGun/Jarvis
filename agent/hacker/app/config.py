import os


class Config:
    # Ollama settings
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_PLANNER_MODEL: str = os.getenv("OLLAMA_PLANNER_MODEL", "llama2-uncensored:7b")
    OLLAMA_COMPILER_MODEL: str = os.getenv("OLLAMA_COMPILER_MODEL", "llama3.1:8b")

    # Agent settings
    MAX_STEPS: int = int(os.getenv("HACKER_MAX_STEPS", "10"))
    MAX_COMPILER_RETRIES: int = int(os.getenv("HACKER_MAX_COMPILER_RETRIES", "3"))

    # Command allowlist - commands that are allowed to execute
    # Empty list means all commands are allowed
    COMMAND_ALLOWLIST: list[str] = []

    # Dangerous patterns to block
    DANGEROUS_PATTERNS: list[str] = [
        "rm -rf /",
        "rm -rf /*",
        "> /dev/sda",
        "mkfs",
        ":(){:|:&};:",  # fork bomb
        "dd if=/dev/zero",
        "chmod -R 777 /",
        "shutdown",
        "reboot",
        "init 0",
        "init 6",
    ]


config = Config()
