"""Legal RAG agent configuration."""

import os


class LegalRagConfig:
    PORT = int(os.getenv("PORT", "8903"))
    AGENT_ID = os.getenv("AGENT_ID", "legal-rag")

    # LLM — switch via LLM_PROVIDER=anthropic|openai
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))

    # Storage paths (relative to the agent's working directory)
    DATA_DIR = os.getenv("LEGAL_RAG_DATA_DIR", "./data")
    FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "./data/faiss.index")
    BM25_PATH = os.getenv("BM25_PATH", "./data/bm25.pkl")
    GRAPH_PATH = os.getenv("GRAPH_PATH", "./data/kg.gpickle")
    CHUNKS_PATH = os.getenv("CHUNKS_PATH", "./data/chunks.pkl")

    # Embedding / retrieval models — bge-m3 is multilingual (100+ languages)
    BGE_MODEL = os.getenv("BGE_MODEL", "BAAI/bge-m3")
    RERANKER_MODEL = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
    # Reranker is opt-in: BAAI/bge-reranker-v2-m3 is XLM-RoBERTa (~1.1 GB) and
    # segfaults on certain macOS Python builds at load. RRF fusion alone gives
    # decent recall; enable reranking only when you've verified it doesn't crash.
    ENABLE_RERANKER = os.getenv("ENABLE_RERANKER", "false").lower() in ("true", "1", "yes")
    RERANKER_USE_FP16 = os.getenv("RERANKER_USE_FP16", "false").lower() in ("true", "1", "yes")
    TOP_K_DENSE = int(os.getenv("TOP_K_DENSE", "30"))
    TOP_K_SPARSE = int(os.getenv("TOP_K_SPARSE", "30"))
    TOP_K_FUSED = int(os.getenv("TOP_K_FUSED", "20"))
    TOP_K_RERANKED = int(os.getenv("TOP_K_RERANKED", "10"))
    RRF_K = int(os.getenv("RRF_K", "60"))
    RRF_WEIGHT_DENSE = float(os.getenv("RRF_WEIGHT_DENSE", "0.6"))
    RRF_WEIGHT_SPARSE = float(os.getenv("RRF_WEIGHT_SPARSE", "0.4"))

    # Graph
    GRAPH_MIN_EDGE_WEIGHT_FOR_EXPANSION = float(os.getenv("GRAPH_MIN_EDGE_WEIGHT", "2.0"))
    PAGERANK_BOOST = float(os.getenv("PAGERANK_BOOST", "5.0"))

    # Ingest — keep concurrency low to stay under free-tier rate limits.
    # OpenAI free/low tiers cap at 10K TPM; semantic alignment fires one
    # request per edge so we also cap how many edges get aligned.
    LLM_EXTRACTION_CONCURRENCY = int(os.getenv("LLM_EXTRACTION_CONCURRENCY", "3"))
    SEMANTIC_ALIGNMENT_MAX_EDGES = int(os.getenv("SEMANTIC_ALIGNMENT_MAX_EDGES", "60"))
    ENABLE_SEMANTIC_ALIGNMENT = os.getenv("ENABLE_SEMANTIC_ALIGNMENT", "true").lower() in ("true", "1", "yes")


config = LegalRagConfig()
