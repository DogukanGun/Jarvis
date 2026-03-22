# =============================================================================
# Swiss Army Knife Security Agent - Multi-Stage Dockerfile
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Go builder – compile Go-based security tools
# ---------------------------------------------------------------------------
FROM golang:1.22-bookworm AS go-builder

# bettercap requires libpcap-dev and libnetfilter-queue-dev to build
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpcap-dev libnetfilter-queue-dev libusb-1.0-0-dev \
    && rm -rf /var/lib/apt/lists/*

RUN go install github.com/bettercap/bettercap@latest || \
    mkdir -p /go/bin && touch /go/bin/bettercap

# ---------------------------------------------------------------------------
# Stage 2: Final image
# ---------------------------------------------------------------------------
FROM python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive

# ---- System packages -------------------------------------------------------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        wget \
        curl \
        libpcap-dev \
        libssl-dev \
        libnetfilter-queue-dev \
        net-tools \
        iproute2 \
        wireless-tools \
        aircrack-ng \
        reaver \
        ettercap-text-only \
        nmap \
        john \
        ruby \
        ruby-dev \
        libffi-dev \
        procps \
    && rm -rf /var/lib/apt/lists/*

# ---- Go binaries from builder -----------------------------------------------
COPY --from=go-builder /go/bin/bettercap /usr/local/bin/bettercap

# ---- Python security tools --------------------------------------------------
RUN pip install --no-cache-dir \
        scapy \
        mitmproxy \
        sqlmap \
        btlejack || true

# ---- Git-cloned tools -------------------------------------------------------
RUN git clone --depth 1 https://github.com/CISOfy/lynis /opt/lynis || true

RUN git clone --depth 1 https://github.com/trustedsec/social-engineer-toolkit /opt/setoolkit && \
    cd /opt/setoolkit && pip install --no-cache-dir -r requirements.txt || true

RUN git clone --depth 1 https://github.com/moloch--/RootTheBox /opt/rootthebox || true

# ---- Metasploit Framework (optional - large install) -------------------------
RUN curl -fsSL https://raw.githubusercontent.com/rapid7/metasploit-omnibus/master/config/templates/metasploit-framework-wrappers/msfupdate.erb > /tmp/msfinstall && \
    chmod 755 /tmp/msfinstall && \
    /tmp/msfinstall && \
    rm -f /tmp/msfinstall || true

ENV PATH="/opt/metasploit-framework/bin:$PATH"

# ---- C2 binaries (optional) -------------------------------------------------
RUN wget -qO /usr/local/bin/sliver-server \
        "https://github.com/BishopFox/sliver/releases/latest/download/sliver-server_linux" && \
    chmod +x /usr/local/bin/sliver-server || true

# ---- Application setup ------------------------------------------------------
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY run_server.py .
COPY run_kafka_consumer.py .

EXPOSE 8787

CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8787"]
