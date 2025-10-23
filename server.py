"""
FastAPI server for HR Knowledge Base Agent.
Provides API endpoints to interact with the HR agent functionality.
"""
import os
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

from .hr_agent import HRKnowledgeBaseAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global agent instance
agent: Optional[HRKnowledgeBaseAgent] = None


class QueryRequest(BaseModel):
    """Request model for employee information queries."""
    query: str = Field(..., description="Natural language query about employee information")
    template_type: str = Field(default="B1", description="Template type (B1, B2, etc.)")


class QueryResponse(BaseModel):
    """Response model for query results."""
    status: str
    message: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for FastAPI application.
    Replaces deprecated @app.on_event("startup") and @app.on_event("shutdown").
    """
    # Startup
    global agent
    logger.info("Starting HR Knowledge Base Agent...")
    try:
        agent = HRKnowledgeBaseAgent()
        logger.info("HR Knowledge Base Agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize HR agent: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down HR Knowledge Base Agent...")
    agent = None


# Create FastAPI app with lifespan handler
app = FastAPI(
    title="HR Knowledge Base Agent API",
    description="API for generating HR warning documents and managing employee information",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "HR Knowledge Base Agent API",
        "version": "1.0.0",
        "endpoints": {
            "/health": "Health check endpoint",
            "/api/query": "Process employee information queries",
            "/docs": "API documentation (Swagger UI)",
            "/redoc": "API documentation (ReDoc)"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    return {"status": "healthy", "agent": "initialized"}


@app.post("/api/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Process a natural language query to generate HR documents.
    
    Args:
        request: QueryRequest containing the query and template type
        
    Returns:
        QueryResponse with status and message
    """
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        logger.info(f"Processing query: {request.query[:100]}...")
        result = agent.generate_answer(request.query, template_type=request.template_type)
        
        # Parse the JSON result
        import json
        result_dict = json.loads(result)
        
        return QueryResponse(
            status=result_dict.get("status", "unknown"),
            message=result_dict.get("message", "")
        )
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def find_available_port(start_port: int = 8000, max_attempts: int = 10) -> int:
    """
    Find an available port starting from start_port.
    
    Args:
        start_port: The port to start searching from
        max_attempts: Maximum number of ports to try
        
    Returns:
        An available port number
        
    Raises:
        RuntimeError: If no available port is found
    """
    import socket
    
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("0.0.0.0", port))
                logger.info(f"Found available port: {port}")
                return port
        except OSError:
            logger.debug(f"Port {port} is already in use")
            continue
    
    raise RuntimeError(f"No available port found in range {start_port}-{start_port + max_attempts - 1}")


def run_server(host: str = "0.0.0.0", port: Optional[int] = None, auto_port: bool = True):
    """
    Run the FastAPI server with configurable port handling.
    
    Args:
        host: Host address to bind to
        port: Port number to use (default: 8000)
        auto_port: If True, automatically find an available port if the specified port is in use
    """
    if port is None:
        port = int(os.getenv("PORT", "8000"))
    
    if auto_port:
        try:
            port = find_available_port(start_port=port)
        except RuntimeError as e:
            logger.error(f"Failed to find available port: {e}")
            raise
    
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()
