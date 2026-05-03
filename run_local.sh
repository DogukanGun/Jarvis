#!/usr/bin/env bash
# =============================================================================
#  Jarvis – Local macOS Run Script
#  Keeps Kafka/MinIO/Ollama in Docker, runs all agents natively so scapy
#  gets direct access to the host network interfaces.
#
#  Usage:
#    ./run_local.sh --ui web        # Next.js chat UI + monitors
#    ./run_local.sh --ui cli        # Ink terminal CLI (foreground)
#    ./run_local.sh --ui desktop    # Electron desktop app
# =============================================================================
set -uo pipefail

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

# ── PID tracking ──────────────────────────────────────────────────────────────
PIDS=()       # regular background pids
SUDO_PIDS=()  # sudo pids (need sudo kill)

# ── Helpers ───────────────────────────────────────────────────────────────────
info()    { echo -e "${BLUE}[•]${NC} $*"; }
ok()      { echo -e "${GREEN}[✓]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*"; }
die()     { echo -e "${RED}[✗]${NC} $*"; exit 1; }

usage() {
    echo -e "${BOLD}Usage:${NC} $0 --ui <web|cli|desktop>"
    echo ""
    echo -e "  ${CYAN}--ui web${NC}      Start Next.js chat UI + agent monitors"
    echo -e "  ${CYAN}--ui cli${NC}      Start Ink terminal CLI (takes over the terminal)"
    echo -e "  ${CYAN}--ui desktop${NC}  Start Electron desktop app"
    echo ""
    echo "  All options start the full Python backend stack."
    exit 0
}

wait_for_port() {
    local name=$1 port=$2 max=${3:-45}
    local i=0
    printf "${BLUE}[•]${NC} Waiting for %-30s" "$name..."
    while ! nc -z localhost "$port" 2>/dev/null; do
        sleep 1; i=$((i+1))
        if [ $i -ge $max ]; then
            echo -e " ${YELLOW}timeout${NC}"
            warn "  $name not ready on :$port after ${max}s — check logs/$name.log"
            return 1
        fi
    done
    echo -e " ${GREEN}:$port${NC}"
}

# ── Cleanup ───────────────────────────────────────────────────────────────────
cleanup() {
    echo ""
    warn "Shutting down all services..."
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    for pid in "${SUDO_PIDS[@]}"; do
        sudo kill "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null || true
    info "Stopping Docker infrastructure..."
    cd "$ROOT" && docker compose stop zookeeper kafka minio ollama 2>/dev/null || true
    ok "All stopped. Logs saved in ./logs/"
}
trap cleanup SIGINT SIGTERM EXIT

# =============================================================================
#  PARSE FLAGS
# =============================================================================
UI_MODE=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --ui)       UI_MODE="${2:-}"; shift 2 ;;
        --ui=*)     UI_MODE="${1#--ui=}"; shift ;;
        -h|--help)  usage ;;
        *)          die "Unknown argument: $1. Run with --help for usage." ;;
    esac
done

if [[ -z "$UI_MODE" ]]; then
    echo -e "${RED}[✗]${NC} Missing required flag: --ui <web|cli|desktop>"
    echo ""
    usage
fi

case "$UI_MODE" in
    web|cli|desktop) ;;
    *) die "Unknown --ui mode: '$UI_MODE'. Choose web, cli, or desktop." ;;
esac

# =============================================================================
#  HEADER
# =============================================================================
echo -e "${BOLD}${CYAN}"
echo "  ╔════════════════════════════════════════╗"
echo "  ║        Jarvis – Local macOS Run        ║"
printf "  ║     UI mode: %-26s║\n" "$UI_MODE"
echo "  ╚════════════════════════════════════════╝"
echo -e "${NC}"

# =============================================================================
#  PREREQUISITES
# =============================================================================
info "Checking prerequisites..."
for cmd in python3 docker nc; do
    command -v "$cmd" &>/dev/null || die "Missing required tool: $cmd"
done

# bun (needed for cli mode; optional otherwise but we check anyway)
BUN_BIN=""
if command -v bun &>/dev/null; then
    BUN_BIN="$(command -v bun)"
elif [ -x "$HOME/.bun/bin/bun" ]; then
    BUN_BIN="$HOME/.bun/bin/bun"
fi

if [[ "$UI_MODE" == "cli" && -z "$BUN_BIN" ]]; then
    die "bun is required for --ui cli. Install: curl -fsSL https://bun.sh/install | bash"
fi

# node/npm needed for web mode
if [[ "$UI_MODE" == "web" || "$UI_MODE" == "desktop" ]]; then
    for cmd in node npm; do
        command -v "$cmd" &>/dev/null || die "Missing required tool: $cmd (needed for --ui $UI_MODE)"
    done
fi

ok "Prerequisites OK"

# =============================================================================
#  ENVIRONMENT
# =============================================================================
if [ -f "$ROOT/.env" ]; then
    set -a; source "$ROOT/.env"; set +a
    ok "Loaded .env"
fi

[ -z "${OPENAI_API_KEY:-}" ] && die "OPENAI_API_KEY is not set. Add it to .env or: export OPENAI_API_KEY=sk-..."
OPENAI_MODEL="${OPENAI_MODEL:-gpt-4o}"

export KAFKA_BROKERS="localhost:9094"
export MINIO_ENDPOINT="localhost:9000"
export MINIO_ACCESS_KEY="minioadmin"
export MINIO_SECRET_KEY="minioadmin"
export MINIO_BUCKET="jarvis"
export MINIO_USE_SSL="false"
export OLLAMA_HOST="http://localhost:11434"
export LLM_PROVIDER="openai"
export OPENAI_API_KEY="$OPENAI_API_KEY"
export OPENAI_MODEL="$OPENAI_MODEL"
export ENABLE_GROUP_LAYER="true"
export GROUP_ID="jarvis-main"

export SWISS_KNIFE_BASE_URL="http://localhost:8787"
export THINKER_BASE_URL="http://localhost:8585"
export MEMORY_BASE_URL="http://localhost:8686"
export WEB_FETCHER_BASE_URL="http://localhost:8099"
export VISION_BASE_URL="http://localhost:8500"
export CODE_ANALYZER_BASE_URL="http://localhost:8900"
export SOLANA_TRADER_BASE_URL="http://localhost:8901"
export SOLANA_STRATEGY_BASE_URL="http://localhost:8902"
export LEGAL_RAG_BASE_URL="http://localhost:8903"
export NEXT_PUBLIC_ROUTER_URL="http://localhost:8888"

# =============================================================================
#  DOCKER INFRASTRUCTURE
# =============================================================================
info "Stopping any running agent containers (keeping infra)..."
cd "$ROOT"
docker compose stop \
    router swiss-army-knife swiss-army-knife-kafka-consumer \
    web-fetcher web-fetcher-kafka-consumer thinker memory-worker \
    router-ui thinker-monitor memory-monitor swiss-army-knife-monitor \
    2>/dev/null || true

info "Starting Docker infrastructure (Kafka, MinIO, Ollama)..."
docker compose up -d zookeeper kafka minio ollama 2>/dev/null

info "Waiting for Kafka broker..."
until docker compose exec -T kafka \
    kafka-broker-api-versions --bootstrap-server localhost:9092 &>/dev/null; do
    sleep 3
done
ok "Kafka ready"

# =============================================================================
#  VENV HELPER
# =============================================================================
setup_venv() {
    local dir=$1 req=$2
    local venv="$dir/.venv"
    if [ ! -d "$venv" ]; then
        info "  Creating venv for $(basename "$dir")..."
        python3 -m venv "$venv"
    fi
    info "  Installing deps for $(basename "$dir")..."
    "$venv/bin/pip" install -q --upgrade pip
    "$venv/bin/pip" install -q -r "$req"
    ok "  $(basename "$dir") deps ready"
}

# Bootstrap a Node service: idempotent npm install if node_modules is missing.
# Does NOT start the service — used for agents Electron spawns later (e.g. the
# Solana trader, which needs the in-process loopback signer creds).
setup_node_deps() {
    local dir=$1
    if [ ! -d "$dir/node_modules" ]; then
        info "  npm install for $(basename "$dir") (first run)..."
        ( cd "$dir" && npm install --silent ) > "$LOG_DIR/$(basename "$dir")-install.log" 2>&1 || \
            warn "  $(basename "$dir") npm install failed — see $LOG_DIR/$(basename "$dir")-install.log"
    fi
    ok "  $(basename "$dir") deps ready"
}

# =============================================================================
#  PYTHON BACKEND SERVICES  (always started regardless of --ui)
# =============================================================================
echo ""
echo -e "${BOLD}── Python backend ───────────────────────────────────${NC}"

# 1. Memory Worker
DIR="$ROOT/agent/memory/episodic"
setup_venv "$DIR" "$DIR/app/requirements.txt"
info "Starting memory-worker..."
( cd "$DIR" && AGENT_ID=memory-worker PORT=8686 \
    "$DIR/.venv/bin/python" run_server.py ) \
    > "$LOG_DIR/memory-worker.log" 2>&1 &
PIDS+=($!)

# 2. Web Fetcher
DIR="$ROOT/agent/web_fetcher"
setup_venv "$DIR" "$DIR/requirements.txt"
info "Installing playwright browsers (first run only)..."
"$DIR/.venv/bin/python" -m playwright install chromium --quiet 2>/dev/null || true
info "Starting web-fetcher..."
( cd "$DIR" && AGENT_ID=web-fetcher PORT=8099 \
    "$DIR/.venv/bin/python" -m uvicorn main:app \
    --host 0.0.0.0 --port 8099 ) \
    > "$LOG_DIR/web-fetcher.log" 2>&1 &
PIDS+=($!)

# 3. Web Fetcher Kafka Consumer
info "Starting web-fetcher-kafka-consumer..."
( cd "$DIR" && AGENT_ID=web-fetcher \
    "$DIR/.venv/bin/python" run_kafka_consumer.py ) \
    > "$LOG_DIR/web-fetcher-kafka-consumer.log" 2>&1 &
PIDS+=($!)

# 4. Thinker
DIR="$ROOT/agent/thinker"
setup_venv "$DIR" "$DIR/requirements.txt"
info "Starting thinker..."
( cd "$DIR" && AGENT_ID=thinker PORT=8585 \
    "$DIR/.venv/bin/python" -m src.server ) \
    > "$LOG_DIR/thinker.log" 2>&1 &
PIDS+=($!)

# 5. Router
DIR="$ROOT/agent/router"
setup_venv "$DIR" "$DIR/requirements.txt"
info "Starting router..."
( cd "$DIR" && AGENT_ID=router PORT=8888 ENABLE_KAFKA_CONSUMER=true \
    "$DIR/.venv/bin/python" -m uvicorn app.server:app \
    --host 0.0.0.0 --port 8888 ) \
    > "$LOG_DIR/router.log" 2>&1 &
PIDS+=($!)

# 6. Face API — replaced by local biometric auth (WebAuthn), no service needed

# 7. Vision Service
DIR="$ROOT/agent/vision"
setup_venv "$DIR" "$DIR/requirements.txt"
info "Starting vision..."
( cd "$DIR" && AGENT_ID=vision PORT=8500 \
    "$DIR/.venv/bin/python" -m uvicorn app.server:app \
    --host 0.0.0.0 --port 8500 ) \
    > "$LOG_DIR/vision.log" 2>&1 &
PIDS+=($!)

# 8. Code Analyzer
DIR="$ROOT/agent/code-analyzer"
setup_venv "$DIR" "$DIR/requirements.txt"
info "Starting code-analyzer..."
( cd "$DIR" && AGENT_ID=code-analyzer PORT=8900 INDEXER_PORT=8901 \
    CODE_ANALYZER_BASE_URL=http://localhost:8900 \
    OPENAI_API_KEY="$OPENAI_API_KEY" LLM_PROVIDER=openai \
    KAFKA_BROKERS=localhost:9094 \
    "$DIR/.venv/bin/python" run_server.py ) \
    > "$LOG_DIR/code-analyzer.log" 2>&1 &
PIDS+=($!)

# 9. Legal RAG
DIR="$ROOT/agent/legal-rag"
setup_venv "$DIR" "$DIR/requirements.txt"
info "Starting legal-rag..."
( cd "$DIR" && AGENT_ID=legal-rag PORT=8903 \
    LEGAL_RAG_BASE_URL="$LEGAL_RAG_BASE_URL" \
    OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
    OPENAI_MODEL="${LEGAL_RAG_OPENAI_MODEL:-gpt-4o-mini}" \
    ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}" \
    LLM_PROVIDER="${LLM_PROVIDER:-openai}" \
    ENABLE_RERANKER="${LEGAL_RAG_ENABLE_RERANKER:-false}" \
    BGE_MODEL="${LEGAL_RAG_BGE_MODEL:-BAAI/bge-m3}" \
    "$DIR/.venv/bin/python" run_server.py ) \
    > "$LOG_DIR/legal-rag.log" 2>&1 &
PIDS+=($!)

# 10. Solana agents (deps only — Electron spawns the actual processes after
#     wallet unlock so they can receive the loopback signer creds).
info "Bootstrapping Solana trader (npm install if needed)..."
setup_node_deps "$ROOT/agent/solana-trader"

info "Bootstrapping Solana strategy (venv if needed)..."
setup_venv "$ROOT/agent/solana-strategy" "$ROOT/agent/solana-strategy/requirements.txt"
ok "Solana agents ready — Electron will spawn them on wallet unlock"

# 9. Swiss Army Knife (sudo for scapy raw sockets)
DIR="$ROOT/agent/swiss-army-knife"
setup_venv "$DIR" "$DIR/requirements.txt"
info "Starting swiss-army-knife ${YELLOW}(sudo required for scapy)${NC}..."
( cd "$DIR" && sudo -E \
    OPENAI_API_KEY="$OPENAI_API_KEY" OPENAI_MODEL="$OPENAI_MODEL" \
    LLM_PROVIDER=openai KAFKA_BROKERS=localhost:9094 \
    ENABLE_GROUP_LAYER=true GROUP_ID=jarvis-main \
    AGENT_ID=swiss-army-knife PORT=8787 CONFIRMATION_TIMEOUT=300 \
    "$DIR/.venv/bin/python" -m uvicorn app.server:app \
    --host 0.0.0.0 --port 8787 ) \
    > "$LOG_DIR/swiss-army-knife.log" 2>&1 &
SUDO_PIDS+=($!)

info "Starting swiss-army-knife-kafka-consumer ${YELLOW}(sudo)${NC}..."
( cd "$DIR" && sudo -E \
    OPENAI_API_KEY="$OPENAI_API_KEY" OPENAI_MODEL="$OPENAI_MODEL" \
    LLM_PROVIDER=openai KAFKA_BROKERS=localhost:9094 \
    ENABLE_GROUP_LAYER=true GROUP_ID=jarvis-main \
    AGENT_ID=swiss-army-knife \
    "$DIR/.venv/bin/python" run_kafka_consumer.py ) \
    > "$LOG_DIR/swiss-army-knife-kafka-consumer.log" 2>&1 &
SUDO_PIDS+=($!)

# ── Wait for Python services ──────────────────────────────────────────────────
echo ""
info "Waiting for Python services to be ready..."
wait_for_port "memory-worker"    8686
wait_for_port "web-fetcher"      8099
wait_for_port "thinker"          8585
wait_for_port "router"           8888
wait_for_port "swiss-army-knife" 8787
wait_for_port "vision"           8500
wait_for_port "code-analyzer"    8900
wait_for_port "legal-rag"        8903

# =============================================================================
#  UI LAYER  (selected by --ui flag)
# =============================================================================
echo ""
echo -e "${BOLD}── UI: $UI_MODE ─────────────────────────────────────────${NC}"

start_next_ui() {
    local name=$1 dir=$2 port=$3
    if [ ! -d "$dir/node_modules" ]; then
        info "  npm install for $name (first run)..."
        ( cd "$dir" && npm install --silent ) 2>/dev/null
    fi
    info "Starting $name on :$port..."
    ( cd "$dir" && NEXT_PUBLIC_ROUTER_URL="$NEXT_PUBLIC_ROUTER_URL" \
        npm run dev -- -p "$port" ) \
        > "$LOG_DIR/$name.log" 2>&1 &
    PIDS+=($!)
}

if [[ "$UI_MODE" == "web" ]]; then
    start_next_ui "router-ui"               "$ROOT/agent/router/ui"               3002
    start_next_ui "swiss-army-knife-monitor" "$ROOT/agent/swiss-army-knife/monitor" 3003
    start_next_ui "thinker-monitor"         "$ROOT/agent/thinker/monitor"          3006
    start_next_ui "memory-monitor"          "$ROOT/agent/memory/monitor"           3001

    echo ""
    info "Waiting for Next.js UIs (may take ~10s on first start)..."
    wait_for_port "router-ui"           3002 60
    wait_for_port "swiss-knife-monitor" 3003 60
    wait_for_port "thinker-monitor"     3006 60
    wait_for_port "memory-monitor"      3001 60

elif [[ "$UI_MODE" == "desktop" ]]; then
    DIR="$ROOT/desktop"
    if [ ! -d "$DIR/node_modules" ]; then
        info "  npm install for desktop (first run)..."
        ( cd "$DIR" && npm install --silent ) 2>/dev/null
    fi
    info "Starting Electron desktop app..."
    ( cd "$DIR" && npm run dev ) \
        > "$LOG_DIR/desktop.log" 2>&1 &
    PIDS+=($!)
    ok "Desktop app launching (Electron window will open shortly)"

elif [[ "$UI_MODE" == "cli" ]]; then
    # Ensure CLI deps are installed
    CLI_DIR="$ROOT/cli"
    if [ ! -d "$CLI_DIR/node_modules" ]; then
        info "  bun install for cli (first run)..."
        ( cd "$CLI_DIR" && "$BUN_BIN" install --silent ) 2>/dev/null
    fi
    ok "CLI deps ready"
fi

# =============================================================================
#  DONE BANNER
# =============================================================================
echo ""
echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}  ✓  Jarvis backend running  [--ui $UI_MODE]${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [[ "$UI_MODE" == "web" ]]; then
    echo -e "  ${BOLD}Chat UI${NC}              ${CYAN}http://localhost:3002${NC}"
    echo -e "  ${BOLD}SAK Monitor${NC}          ${CYAN}http://localhost:3003${NC}"
    echo -e "  ${BOLD}Thinker Monitor${NC}      ${CYAN}http://localhost:3006${NC}"
    echo -e "  ${BOLD}Memory Monitor${NC}       ${CYAN}http://localhost:3001${NC}"
    echo ""
elif [[ "$UI_MODE" == "desktop" ]]; then
    echo -e "  ${BOLD}Desktop App${NC}          ${CYAN}(Electron window)${NC}"
    echo ""
elif [[ "$UI_MODE" == "cli" ]]; then
    echo -e "  ${BOLD}CLI${NC}  Launching Jarvis terminal..."
    echo ""
fi

echo -e "  ${BOLD}Router API${NC}           ${CYAN}http://localhost:8888${NC}"
echo -e "  ${BOLD}Swiss-knife${NC}          ${CYAN}http://localhost:8787${NC}  ${YELLOW}(sudo)${NC}"
echo -e "  ${BOLD}Thinker${NC}              ${CYAN}http://localhost:8585${NC}"
echo -e "  ${BOLD}Memory${NC}               ${CYAN}http://localhost:8686${NC}"
echo -e "  ${BOLD}Web Fetcher${NC}          ${CYAN}http://localhost:8099${NC}"
echo -e "  ${BOLD}Face API${NC}             ${CYAN}http://localhost:8400${NC}"
echo -e "  ${BOLD}Vision${NC}               ${CYAN}http://localhost:8500${NC}"
echo -e "  ${BOLD}Code Analyzer${NC}        ${CYAN}http://localhost:8900${NC}"
echo -e "  ${BOLD}Solana Trader${NC}        ${CYAN}http://localhost:8901${NC}  ${YELLOW}(Electron spawns after wallet unlock)${NC}"
echo -e "  ${BOLD}Solana Strategy${NC}      ${CYAN}http://localhost:8902${NC}  ${YELLOW}(Electron spawns after wallet unlock)${NC}"
echo -e "  ${BOLD}Legal RAG${NC}            ${CYAN}http://localhost:8903${NC}"
echo -e "  ${BOLD}Kafka${NC}                ${CYAN}localhost:9094${NC}"
echo -e "  ${BOLD}MinIO Console${NC}        ${CYAN}http://localhost:9001${NC}"
echo ""
echo -e "  Logs: ${YELLOW}./logs/<service>.log${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [[ "$UI_MODE" == "cli" ]]; then
    # Hand the terminal over to the CLI — blocks until user exits
    echo -e "  Press ${BOLD}Ctrl+C${NC} or type ${BOLD}/exit${NC} inside Jarvis to stop everything"
    echo ""
    "$BUN_BIN" "$ROOT/cli/src/main.tsx"
else
    echo -e "  Press ${BOLD}Ctrl+C${NC} to stop everything"
    echo ""
    wait
fi
