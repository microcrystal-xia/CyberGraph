"""Configuration for CyberGraph experiments."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env", override=True)


class Config:
    # Neo4j
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

    # LLM
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # "openai" or "anthropic"
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

    # Paths
    PROJECT_ROOT = _PROJECT_ROOT
    NEO4J_DIR = _PROJECT_ROOT / "neo4j"
    PROMPTS_DIR = _PROJECT_ROOT / "n8n" / "prompts"
    RESULTS_DIR = _PROJECT_ROOT / "cybergraph_exp" / "results"

    @classmethod
    def validate(cls):
        errors = []
        if cls.LLM_PROVIDER == "openai" and not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY required when LLM_PROVIDER=openai")
        if cls.LLM_PROVIDER == "anthropic" and not cls.ANTHROPIC_API_KEY:
            errors.append("ANTHROPIC_API_KEY required when LLM_PROVIDER=anthropic")
        if errors:
            raise ValueError("Config errors: " + "; ".join(errors))
        return True
