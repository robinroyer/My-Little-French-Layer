"""Configuration management for MLFL web application."""
import os
from dataclasses import dataclass
from typing import Literal


@dataclass
class Config:
    """Application configuration from environment variables."""

    # LLM Configuration
    llm_provider: Literal["ollama", "claude"] = "ollama"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"
    anthropic_api_key: str | None = None
    claude_model: str = "claude-sonnet-4-20250514"

    # Qdrant Configuration
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "law_library"

    # Rag research parameters
    top_k: int = 5
    score_threshold: float = 0.5

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8080

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        llm_provider_str = os.getenv("LLM_PROVIDER", "ollama")
        if llm_provider_str not in ("ollama", "claude"):
            llm_provider_str = "ollama"
        
        return cls(
            llm_provider=llm_provider_str,
            ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen3:4b"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            claude_model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
            qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            qdrant_collection=os.getenv("QDRANT_COLLECTION", "law_library"),
            top_k=int(os.getenv("RAG_TOP_K", "5")),
            score_threshold=float(os.getenv("RAG_SCORE_THRESHOLD", "0.7")),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8080")),
        )


# Global config instance
config = Config.from_env()
