from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent  # hackerrank-orchestrate-may26/

class Settings(BaseSettings):
    # LLM
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # Retrieval
    TOP_K_TFIDF: int = 20
    TOP_K_FINAL: int = 3
    MIN_RELEVANCE_SCORE: float = 0.15  # below this → escalate, never hallucinate

    # Paths
    CORPUS_DIR: str = str(BASE_DIR / "data")
    INPUT_CSV: str = str(BASE_DIR / "support_tickets" / "support_tickets.csv")
    OUTPUT_CSV: str = str(BASE_DIR / "support_tickets" / "output.csv")
    SAMPLE_CSV: str = str(BASE_DIR / "support_tickets" / "sample_support_tickets.csv")
    INDEX_CACHE: str = str(BASE_DIR / "code" / ".cache" / "tfidf_index.pkl")

    # Agent
    MAX_CONCURRENT: int = 10
    MAX_RESPONSE_TOKENS: int = 400

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"

settings = Settings()