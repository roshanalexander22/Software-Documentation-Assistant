"""
Configuration settings for the Software Documentation Assistant RAG system.
Uses pydantic-settings to allow environment variable overrides.
"""

from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Base paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    DOCS_DIR: Path = DATA_DIR / "docs"
    RESULTS_DIR: Path = BASE_DIR / "results"
    REPORTS_DIR: Path = BASE_DIR / "reports"
    NOTEBOOKS_DIR: Path = BASE_DIR / "notebooks"
    INDEX_CACHE_DIR: Path = RESULTS_DIR / "index_cache"

    # Ingestion & Chunking
    CHUNK_SIZE: int = Field(default=650, description="Target character count per chunk")
    CHUNK_OVERLAP: int = Field(default=100, description="Overlap character count between chunks")
    MIN_CHUNK_SIZE: int = Field(default=80, description="Minimum characters for a valid chunk")

    # Embeddings
    EMBEDDING_MODEL: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Pretrained sentence-transformers embedding model"
    )
    EMBEDDING_DIM: int = Field(default=384, description="Embedding vector dimension")

    # Retrieval & Search
    RETRIEVAL_TOP_K: int = Field(default=4, description="Default number of passages retrieved")
    HYBRID_ALPHA: float = Field(default=0.65, description="Dense weight (1-alpha is sparse weight)")
    ABSTENTION_SIMILARITY_THRESHOLD: float = Field(
        default=0.38,
        description="Minimum similarity score below which the system abstains from answering"
    )

    # Large Language Model Generation
    GEMINI_API_KEY: str | None = Field(default=None, description="Google Gemini API Key")
    GEMINI_MODEL: str = Field(default="gemini-2.5-flash", description="Target Gemini model")
    GENERATION_TEMPERATURE: float = Field(default=0.0, description="Sampling temperature for grounded generation")

    # Web Server
    SERVER_HOST: str = Field(default="127.0.0.1", description="FastAPI host")
    SERVER_PORT: int = Field(default=8000, description="FastAPI port")
    DEBUG: bool = Field(default=False, description="Debug mode flag")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


# Singleton instance
settings = Settings()

# Ensure runtime directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.DOCS_DIR.mkdir(parents=True, exist_ok=True)
settings.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
settings.INDEX_CACHE_DIR.mkdir(parents=True, exist_ok=True)
