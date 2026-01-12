"""
Mem0 FastAPI Server
REST API for self-hosted Mem0 memory operations
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from mem0 import Memory
from config import get_mem0_config, get_config
import uvicorn
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Mem0 Memory API",
    description="Self-hosted memory layer API for AI agents and assistants",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware to allow external access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Mem0
config = get_config()
memory = None


@app.on_event("startup")
async def startup_event():
    """Initialize Mem0 on startup"""
    global memory
    try:
        logger.info("Initializing Mem0 memory layer...")
        mem0_config = get_mem0_config(use_graph_store=True)
        memory = Memory.from_config(mem0_config)
        logger.info("Mem0 initialized successfully!")
    except Exception as e:
        logger.error(f"Failed to initialize Mem0: {e}")
        raise


# Pydantic Models for Request/Response
class AddMemoryRequest(BaseModel):
    text: str = Field(..., description="Memory text content")
    user_id: str = Field(..., description="User identifier")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "I love playing basketball on weekends",
                "user_id": "user123",
                "metadata": {"category": "hobbies"}
            }
        }


class AddMessagesRequest(BaseModel):
    messages: List[Dict[str, str]] = Field(..., description="Conversation messages")
    user_id: str = Field(..., description="User identifier")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "messages": [
                    {"role": "user", "content": "Hi, I'm Alex. I love basketball."},
                    {"role": "assistant", "content": "Nice to meet you Alex!"}
                ],
                "user_id": "user123"
            }
        }


class SearchMemoryRequest(BaseModel):
    query: str = Field(..., description="Search query")
    user_id: str = Field(..., description="User identifier")
    limit: int = Field(5, ge=1, le=100, description="Maximum number of results")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "What are my hobbies?",
                "user_id": "user123",
                "limit": 5
            }
        }


class UpdateMemoryRequest(BaseModel):
    memory_id: str = Field(..., description="Memory ID to update")
    text: str = Field(..., description="New memory text")
    
    class Config:
        json_schema_extra = {
            "example": {
                "memory_id": "mem_123abc",
                "text": "I love playing basketball and tennis on weekends"
            }
        }


class DeleteMemoryRequest(BaseModel):
    memory_id: str = Field(..., description="Memory ID to delete")


class GetAllMemoriesRequest(BaseModel):
    user_id: str = Field(..., description="User identifier")


class MemoryResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "name": "Mem0 Memory API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if memory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Memory service not initialized"
        )
    
    return {
        "status": "healthy",
        "service": "mem0",
        "config": {
            "vector_store": "qdrant",
            "llm": config.ollama_llm_model,
            "embedder": config.ollama_embedding_model,
            "graph_store": "neo4j"
        }
    }


@app.post("/memory/add", response_model=MemoryResponse)
async def add_memory(request: AddMemoryRequest):
    """Add a new memory from text"""
    try:
        result = memory.add(
            request.text,
            user_id=request.user_id,
            metadata=request.metadata
        )
        return MemoryResponse(
            success=True,
            message="Memory added successfully",
            data=result
        )
    except Exception as e:
        logger.error(f"Error adding memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/memory/add-messages", response_model=MemoryResponse)
async def add_messages(request: AddMessagesRequest):
    """Add memories from conversation messages"""
    try:
        result = memory.add(
            request.messages,
            user_id=request.user_id,
            metadata=request.metadata
        )
        return MemoryResponse(
            success=True,
            message="Memories from messages added successfully",
            data=result
        )
    except Exception as e:
        logger.error(f"Error adding messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/memory/search", response_model=MemoryResponse)
async def search_memories(request: SearchMemoryRequest):
    """Search for relevant memories"""
    try:
        results = memory.search(
            request.query,
            user_id=request.user_id,
            limit=request.limit
        )
        return MemoryResponse(
            success=True,
            message=f"Found {len(results)} memories",
            data=results
        )
    except Exception as e:
        logger.error(f"Error searching memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/memory/get-all", response_model=MemoryResponse)
async def get_all_memories(request: GetAllMemoriesRequest):
    """Get all memories for a user"""
    try:
        memories = memory.get_all(user_id=request.user_id)
        return MemoryResponse(
            success=True,
            message=f"Retrieved {len(memories)} memories",
            data=memories
        )
    except Exception as e:
        logger.error(f"Error getting all memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.put("/memory/update", response_model=MemoryResponse)
async def update_memory(request: UpdateMemoryRequest):
    """Update an existing memory"""
    try:
        result = memory.update(
            memory_id=request.memory_id,
            data=request.text
        )
        return MemoryResponse(
            success=True,
            message="Memory updated successfully",
            data=result
        )
    except Exception as e:
        logger.error(f"Error updating memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.delete("/memory/delete", response_model=MemoryResponse)
async def delete_memory(request: DeleteMemoryRequest):
    """Delete a specific memory"""
    try:
        result = memory.delete(memory_id=request.memory_id)
        return MemoryResponse(
            success=True,
            message="Memory deleted successfully",
            data=result
        )
    except Exception as e:
        logger.error(f"Error deleting memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.delete("/memory/delete-all", response_model=MemoryResponse)
async def delete_all_memories(request: GetAllMemoriesRequest):
    """Delete all memories for a user"""
    try:
        result = memory.delete_all(user_id=request.user_id)
        return MemoryResponse(
            success=True,
            message="All memories deleted successfully",
            data=result
        )
    except Exception as e:
        logger.error(f"Error deleting all memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


def start_server(host: str = "0.0.0.0", port: int = 8000):
    """Start the FastAPI server"""
    logger.info(f"Starting Mem0 API server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import sys
    
    # Get host and port from command line or use defaults
    host = sys.argv[1] if len(sys.argv) > 1 else "0.0.0.0"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
    
    start_server(host=host, port=port)

