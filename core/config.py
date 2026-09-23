"""Settings shared by the ingestion scripts and the Streamlit app."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CASE_NAME = "MNR v Cameron"
CASE_CITATION = "[1974] SCR 1062"

CHUNKS_PATH = ROOT / "data" / "chunks.json"
CHROMA_PATH = ROOT / "chroma_db"
COLLECTION = "cameron_structured"

EMBED_MODEL = "text-embedding-3-large"   # must be the same at build time and query time
CHAT_MODEL = "gpt-4o"
TOP_K = 4                                # chunks retrieved per question


def get_api_key() -> str | None:
    """Find the developer's OpenAI key for the offline scripts.

    Looks in, in order: the OPENAI_API_KEY environment variable, a .env file,
    then .streamlit/secrets.toml. (The deployed app reads st.secrets instead.)
    """
    if os.getenv("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"]
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
        if os.getenv("OPENAI_API_KEY"):
            return os.environ["OPENAI_API_KEY"]
    except ImportError:
        pass
    secrets = ROOT / ".streamlit" / "secrets.toml"
    if secrets.exists():
        import tomllib
        data = tomllib.loads(secrets.read_text())
        return data.get("OPENAI_API_KEY")
    return None
