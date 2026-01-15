"""
Mem0 Configuration Module
Manages configuration for self-hosted Mem0 setup with Ollama, Qdrant, and Neo4j
"""

import os
from dotenv import load_dotenv
from typing import Dict, Any

# Load environment variables from .env file
load_dotenv()


class Mem0Config:
    """Configuration class for Mem0 self-hosted setup"""
    
    def __init__(self):
        """Initialize configuration from environment variables"""
        
        # Neo4j Configuration
        self.neo4j_url = os.getenv("NEO4J_URL", "bolt://localhost:7687")
        self.neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "mem0password")
        
        # Qdrant Configuration
        self.qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
        self.qdrant_collection = os.getenv("QDRANT_COLLECTION", "memory_store")
        
        # Ollama Configuration
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_llm_model = os.getenv("OLLAMA_LLM_MODEL", "llama3.1:8b")
        self.ollama_embedding_model = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text:latest")
        
        # Mem0 Settings
        self.embedding_model_dims = int(os.getenv("EMBEDDING_MODEL_DIMS", "768"))
        self.llm_temperature = float(os.getenv("LLM_TEMPERATURE", "0"))
        self.llm_max_tokens = int(os.getenv("LLM_MAX_TOKENS", "2000"))
        
        # Application Settings
        self.default_user_id = os.getenv("DEFAULT_USER_ID", "default_user")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
    
    def get_mem0_config(self) -> Dict[str, Any]:
        """
        Generate Mem0 configuration dictionary
        
        Returns:
            Dict containing complete Mem0 configuration
        """
        config = {
            "version": "v1.1",
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "collection_name": self.qdrant_collection,
                    "host": self.qdrant_host,
                    "port": self.qdrant_port,
                    "embedding_model_dims": self.embedding_model_dims,
                }
            },
            "llm": {
                "provider": "ollama",
                "config": {
                    "model": self.ollama_llm_model,
                    "temperature": self.llm_temperature,
                    "max_tokens": self.llm_max_tokens,
                    "ollama_base_url": self.ollama_base_url,
                }
            },
            "embedder": {
                "provider": "ollama",
                "config": {
                    "model": self.ollama_embedding_model,
                    "ollama_base_url": self.ollama_base_url,
                }
            },
            "graph_store": {
                "provider": "neo4j",
                "config": {
                    "url": self.neo4j_url,
                    "username": self.neo4j_username,
                    "password": self.neo4j_password,
                }
            }
        }
        
        return config
    
    def get_mem0_config_without_graph(self) -> Dict[str, Any]:
        """
        Generate Mem0 configuration without graph store (lighter setup)
        
        Returns:
            Dict containing Mem0 configuration without Neo4j
        """
        config = self.get_mem0_config()
        del config["graph_store"]
        return config
    
    def print_config(self):
        """Print current configuration (excluding passwords)"""
        print("\n" + "="*60)
        print("Mem0 Configuration")
        print("="*60)
        print(f"\nVector Store (Qdrant):")
        print(f"  - Host: {self.qdrant_host}")
        print(f"  - Port: {self.qdrant_port}")
        print(f"  - Collection: {self.qdrant_collection}")
        print(f"  - Embedding Dims: {self.embedding_model_dims}")
        
        print(f"\nLLM (Ollama):")
        print(f"  - Base URL: {self.ollama_base_url}")
        print(f"  - LLM Model: {self.ollama_llm_model}")
        print(f"  - Embedding Model: {self.ollama_embedding_model}")
        print(f"  - Temperature: {self.llm_temperature}")
        print(f"  - Max Tokens: {self.llm_max_tokens}")
        
        print(f"\nGraph Store (Neo4j):")
        print(f"  - URL: {self.neo4j_url}")
        print(f"  - Username: {self.neo4j_username}")
        print(f"  - Password: {'*' * len(self.neo4j_password)}")
        
        print(f"\nApplication:")
        print(f"  - Default User ID: {self.default_user_id}")
        print(f"  - Debug Mode: {self.debug}")
        print("="*60 + "\n")


# Global configuration instance
config = Mem0Config()


def get_config() -> Mem0Config:
    """
    Get the global configuration instance
    
    Returns:
        Mem0Config instance
    """
    return config


def get_mem0_config(use_graph_store: bool = True) -> Dict[str, Any]:
    """
    Get Mem0 configuration dictionary
    
    Args:
        use_graph_store: Whether to include Neo4j graph store (default: True)
    
    Returns:
        Dict containing Mem0 configuration
    """
    if use_graph_store:
        return config.get_mem0_config()
    else:
        return config.get_mem0_config_without_graph()


if __name__ == "__main__":
    # Test configuration
    config.print_config()
    print("\n📋 Full Mem0 Config:")
    import json
    mem0_config = get_mem0_config()
    print(json.dumps(mem0_config, indent=2))

