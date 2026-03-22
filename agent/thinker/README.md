# Thinker — Problem-to-Paper Pipeline

An automated multi-agent system that takes a research topic and produces a full scientific paper draft. It runs a 9-phase pipeline: problem discovery → viability screening → sub-problem decomposition → research swarm → execution planning → code generation → testing → baseline comparison → paper writing.

---

## Prerequisites

- Python 3.11+
- [Qwen CLI](https://github.com/QwenLM/qwen-agent) **or** Claude CLI installed and available in your `PATH`
- An [Anthropic API key](https://console.anthropic.com/)
- A [Tavily API key](https://app.tavily.com/) (for web search)

### Install Qwen CLI (recommended)

```bash
pip install qwen-agent
```

Or to use Claude CLI instead:

```bash
npm install -g @anthropic-ai/claude-code
```

---

## Setup

### 1. Clone / navigate to the project

```bash
cd /path/to/thinker
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
```

---

## Running the App

### Basic usage (default topic, Qwen agent)

```bash
python -m src.main
```

This runs the full pipeline on the default topic: **"LLM efficiency and compression"** using the `qwen` CLI.

### Use Claude CLI instead of Qwen

```bash
python -m src.main --agent claude
```

### Custom research topic

```bash
python -m src.main --topic "transformer attention mechanisms"
```

### Limit scope (useful for testing)

```bash
# Only evaluate 2 problems and process 1 accepted problem
python -m src.main --max-problems 2 --max-accepted 1

# Also limit research sub-tasks to 3
python -m src.main --max-problems 2 --max-accepted 1 --max-research 3
```

### All options

```
python -m src.main [OPTIONS]

Options:
  --topic TEXT         Seed topic for problem discovery
                       (default: "LLM efficiency and compression")
  --agent {qwen,claude}
                       Agent CLI to use as sub-agent runtime
                       (default: qwen)
  --max-problems N     Max number of problems to evaluate
  --max-accepted N     Max number of accepted problems to process
  --max-research N     Max number of sub-agent research tasks to run
```

---

## Quick connectivity test

To verify your API keys and SDK are working before running the full pipeline:

```bash
python test_sdk.py
```

---

## Outputs

All generated artifacts are saved to the `outputs/` directory:

| File / Folder | Description |
|---|---|
| `outputs/problems.json` | Discovered research problems |
| `outputs/sub_agent_reports/` | Per-sub-problem research findings |
| `outputs/execution_plans/` | Structured implementation plans |
| `outputs/code/` | Generated proof-of-concept code |
| `outputs/test_results.json` | Test & validation results |
| `outputs/comparison_report.md` | Comparison against baselines |
| `outputs/paper_draft.md` | Final scientific paper draft |

---

## Pipeline Phases

| # | Phase | What it does |
|---|---|---|
| 1 | Gather | Discovers 4 candidate research problems via web search |
| 2 | Evaluate | Screens each problem for viability |
| 3 | Decompose | Breaks each problem into 5 research sub-problems |
| 4 | Research | Runs a parallel agent swarm to investigate each sub-problem |
| 5 | Plan | Synthesizes findings into a structured execution plan |
| 6 | Code | Generates a proof-of-concept implementation |
| 7 | Test | Executes and validates the implementation |
| 8 | Compare | Compares solution against existing baselines |
| 9 | Write | Generates a full scientific paper draft |

---

## Troubleshooting

**`qwen: command not found`**
Install qwen-agent (`pip install qwen-agent`) or switch to `--agent claude`.

**`ANTHROPIC_API_KEY not set`**
Make sure your `.env` file exists in the project root with valid keys.

**Pipeline stops after Phase 2**
All discovered problems were rejected as not viable. Try a different `--topic` or increase `--max-problems`.
