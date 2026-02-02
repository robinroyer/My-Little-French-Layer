"""FastAPI application for My Little French Lawyer."""
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Response

# Configure logging for telemetry
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("mlfl")
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config import config
from llm import get_llm, invoke_llm
from rag import get_vector_store, check_qdrant_health, retrieve_context, build_prompt, Source

# Initialize FastAPI
app = FastAPI(
    title="My Little French Lawyer",
    description="RAG-powered French legal assistant",
    version="1.0.0",
)

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances (lazy loaded)
_llm = None
_vector_store = None


def get_llm_instance():
    """Get or create LLM instance."""
    global _llm
    if _llm is None:
        _llm = get_llm()
    return _llm


def get_vector_store_instance():
    """Get or create vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = get_vector_store()
    return _vector_store


# Pydantic models
class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: str


class ChatRequest(BaseModel):
    message: str
    history: list[Message] = []
    use_rag: bool = True
    selected_codes: list[str] = []


class SourceResponse(BaseModel):
    content: str
    metadata: dict
    score: float


class ChatResponse(BaseModel):
    response: str
    sources: list[SourceResponse]


class HealthResponse(BaseModel):
    status: str
    provider: str
    qdrant: bool


class ExportRequest(BaseModel):
    history: list[Message]


# API Routes
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a chat message and return response with sources."""
    try:
        llm = get_llm_instance()
        vector_store = get_vector_store_instance()

        # Retrieve context from RAG if enabled
        sources = []
        context = None

        # Telemetry: Log request info
        logger.info("=" * 60)
        logger.info(f"📝 QUERY: {request.message[:100]}{'...' if len(request.message) > 100 else ''}")
        logger.info(f"🔧 RAG ENABLED: {request.use_rag}")
        if request.selected_codes:
            logger.info(f"📚 SELECTED CODES: {request.selected_codes}")

        if request.use_rag and vector_store:
            source_books = request.selected_codes if request.selected_codes else None
            context, source_objs = await asyncio.to_thread(
                retrieve_context,
                vector_store,
                request.message,
                k=config.top_k,
                source_books=source_books,
            )
            sources = [
                SourceResponse(
                    content=s.content,
                    metadata=s.metadata,
                    score=s.score,
                )
                for s in source_objs
            ]

            # Telemetry: Log RAG results
            logger.info(f"📊 RAG RESULTS: {len(sources)} sources found")
            for i, src in enumerate(source_objs, 1):
                source_name = src.metadata.get("source", src.metadata.get("filename", "Unknown"))
                logger.info(f"   [{i}] Score: {src.score:.4f} | Source: {source_name}")
                logger.info(f"       Preview: {src.content[:80]}...")

            if context:
                logger.info(f"📄 CONTEXT LENGTH: {len(context)} chars")
            else:
                logger.info("⚠️  NO CONTEXT RETRIEVED")
        else:
            logger.info("🚫 RAG SKIPPED (disabled or vector store unavailable)")

        # Build prompt with history
        history_dicts = [{"role": m.role, "content": m.content} for m in request.history]
        prompt = build_prompt(request.message, context, history_dicts)

        # Get LLM response
        response_text = await asyncio.to_thread(invoke_llm, llm, prompt)

        logger.info(f"✅ RESPONSE LENGTH: {len(response_text)} chars")
        logger.info("=" * 60)

        return ChatResponse(response=response_text, sources=sources)

    except Exception as e:
        logger.error(f"❌ ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")


@app.get("/api/health", response_model=HealthResponse)
async def health():
    """Check system health."""
    qdrant_ok = await asyncio.to_thread(check_qdrant_health)

    return HealthResponse(
        status="ok" if qdrant_ok else "degraded",
        provider=config.llm_provider,
        qdrant=qdrant_ok,
    )


@app.post("/api/export")
async def export_chat(request: ExportRequest, format: Literal["txt", "md"] = "md"):
    """Export chat history as a file."""
    if not request.history:
        raise HTTPException(status_code=400, detail="No messages to export")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"mlfl_conversation_{timestamp}.{format}"

    if format == "md":
        content = "# My Little French Lawyer - Conversation Export\n\n"
        content += f"*Exported on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n---\n\n"

        for msg in request.history:
            role = "**You**" if msg.role == "user" else "**Assistant**"
            content += f"{role}\n\n{msg.content}\n\n---\n\n"
    else:
        content = "My Little French Lawyer - Conversation Export\n"
        content += f"Exported on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += "=" * 50 + "\n\n"

        for msg in request.history:
            role = "You" if msg.role == "user" else "Assistant"
            content += f"{role}:\n{msg.content}\n\n" + "-" * 30 + "\n\n"

    return Response(
        content=content,
        media_type="text/plain" if format == "txt" else "text/markdown",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        },
    )


# Serve static files (React build)
static_path = Path(__file__).parent.parent / "frontend" / "dist"
if static_path.exists():
    app.mount("/assets", StaticFiles(directory=static_path / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the SPA for all non-API routes."""
        file_path = static_path / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(static_path / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        reload=True,
    )
