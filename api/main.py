"""FastAPI application for Vietnamese Tax Law Explorer backend."""
import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Load environment variables from parent GP directory
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

from api.routers import graph, rag, documents, auth, annotation, stats
from api.db.neo4j import get_neo4j_client
from api.schemas import HealthResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events."""
    # Startup
    logger.info("Starting Vietnamese Tax Law Explorer API...")
    try:
        client = get_neo4j_client()
        if client.verify_connectivity():
            logger.info("Neo4j connection established")
        else:
            logger.warning("Neo4j connection failed during startup")
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")

    yield

    # Shutdown
    logger.info("Shutting down API...")
    try:
        client = get_neo4j_client()
        client.close()
        logger.info("Neo4j connection closed")
    except Exception as e:
        logger.error(f"Error closing Neo4j connection: {e}")


app = FastAPI(
    title="Vietnamese Tax Law Explorer API",
    version="1.0.0",
    description="Backend API for graph visualization and RAG queries on Vietnamese tax law documents",
    lifespan=lifespan
)

# CORS configuration for React dev servers
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite default
        "http://localhost:8080",  # Custom Vite port
        "http://localhost:3000",  # Alternative React port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(graph.router)
app.include_router(rag.router)
app.include_router(documents.router)
app.include_router(auth.router)
app.include_router(annotation.router)
app.include_router(stats.router)


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Check API and Neo4j connectivity."""
    try:
        client = get_neo4j_client()
        connected = client.verify_connectivity()

        if connected:
            node_count = client.get_node_count("Test_rel_2")
            return HealthResponse(
                status="healthy",
                neo4j_connected=True,
                message="All systems operational",
                node_count=node_count
            )
        else:
            return HealthResponse(
                status="degraded",
                neo4j_connected=False,
                message="Neo4j connection unavailable"
            )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            neo4j_connected=False,
            message=f"Health check failed: {str(e)}"
        )


@app.get("/")
async def root():
    """Root endpoint - API info."""
    return {
        "name": "Vietnamese Tax Law Explorer API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health"
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "path": str(request.url),
            "timestamp": datetime.now().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
