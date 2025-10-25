# Jarvis CLI

Command-line interface for the Jarvis AI Agent, allowing you to use Jarvis in CI/CD pipelines and terminal environments.

## Installation

From the `cli` directory:
```bash
go build -o jarvis .
```

## Usage

### Interactive Chat Mode
```bash
./jarvis chat
```

### One-shot Queries
```bash
./jarvis ask "What is the current time?"
./jarvis ask "Read the contents of README.md"
./jarvis ask "Run this Python code: print('Hello World')"
```

### Information Commands
```bash
./jarvis info capabilities  # Show agent capabilities
./jarvis info tools         # Show available tools
./jarvis info version       # Show version information
```

### Configuration

Set your OpenAI API key:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

Or pass it as a flag:
```bash
./jarvis --openai-key="your-api-key" chat
```

### Available Models

- `gpt-4o-mini` (default)
- `gpt-4o`
- `gpt-4`
- `gpt-3.5-turbo`

Example:
```bash
./jarvis --model="gpt-4o" chat
```

## CI/CD Usage

Perfect for automation:
```bash
# In your CI pipeline
./jarvis ask "Run tests and check if they pass"
./jarvis ask "Generate documentation from the code"
./jarvis ask "Check code quality and suggest improvements"
```