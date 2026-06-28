import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    # Fallback to sqlite for testing if DB URL not provided
    SUPABASE_DB_CONN: str = os.getenv("SUPABASE_DB_CONN", "postgresql://postgres:postgres@localhost:5432/postgres")
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "llama-3.3-70b-versatile")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "local")
    
    # Model routing constants
    MODEL_PLANNER: str = "llama-3.3-70b-versatile"
    MODEL_CODER: str = "llama-3.3-70b-versatile"
    MODEL_SPECIALIST: str = "llama-3.3-70b-versatile"

config = Config()
