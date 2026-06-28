import psycopg2
from psycopg2.extras import RealDictCursor
from app.config import config

def get_db_connection():
    """Establishes and returns a connection to the PostgreSQL database."""
    conn = psycopg2.connect(config.SUPABASE_DB_CONN, cursor_factory=RealDictCursor)
    return conn

def init_db():
    """Initializes the database schema including pgvector extension and table creation."""
    conn = get_db_connection()
    try:
        # 1. Enable the pgvector extension in its own isolated transaction
        with conn.cursor() as cur:
            try:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"Warning: Could not enable pgvector extension. Make sure it is supported. Error: {e}")
        
        # 2. Initialize remaining tables and indexes
        with conn.cursor() as cur:
            # Create repositories table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS repositories (
                    id SERIAL PRIMARY KEY,
                    url TEXT NOT NULL,
                    name TEXT,
                    status TEXT,
                    user_id UUID,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Adjust unique constraint for multi-tenancy safely
            try:
                cur.execute("ALTER TABLE repositories DROP CONSTRAINT IF EXISTS repositories_url_key;")
                cur.execute("ALTER TABLE repositories ADD COLUMN IF NOT EXISTS user_id UUID;")
                
                # Check if constraint exists before adding to prevent aborting transaction
                cur.execute("SELECT 1 FROM pg_constraint WHERE conname = 'repositories_url_user_id_key';")
                if not cur.fetchone():
                    cur.execute("ALTER TABLE repositories ADD CONSTRAINT repositories_url_user_id_key UNIQUE (url, user_id);")
            except Exception as e:
                print(f"Warning adjusting unique constraint on repositories: {e}")

            # Create executable_blueprints table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS executable_blueprints (
                    id UUID PRIMARY KEY,
                    repository_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
                    name TEXT,
                    user_id UUID,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            try:
                cur.execute("ALTER TABLE executable_blueprints ADD COLUMN IF NOT EXISTS user_id UUID;")
            except Exception as e:
                print(f"Warning: Could not alter executable_blueprints table. Error: {e}")

            # Create branches table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS branches (
                    id UUID PRIMARY KEY,
                    blueprint_id UUID REFERENCES executable_blueprints(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    active BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Create executable_blueprint_nodes table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS executable_blueprint_nodes (
                    id TEXT NOT NULL,
                    blueprint_id UUID REFERENCES executable_blueprints(id) ON DELETE CASCADE,
                    branch_id UUID REFERENCES branches(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    type TEXT,
                    confidence_score INTEGER,
                    confidence_explanation TEXT,
                    supporting_evidence JSONB,
                    architectural_reasoning_summary TEXT,
                    source_files JSONB,
                    dependency_references JSONB,
                    related_modules JSONB,
                    generated_task TEXT,
                    embedding vector(768),
                    PRIMARY KEY (id, branch_id)
                );
            """)
            
            # Ensure status and explanation columns are present
            try:
                cur.execute("ALTER TABLE executable_blueprint_nodes ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'todo';")
                cur.execute("ALTER TABLE executable_blueprint_nodes ADD COLUMN IF NOT EXISTS confidence_explanation TEXT;")
            except Exception as e:
                print(f"Warning: Could not alter executable_blueprint_nodes table. Error: {e}")

            # Create executable_blueprint_edges table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS executable_blueprint_edges (
                    id TEXT NOT NULL,
                    blueprint_id UUID REFERENCES executable_blueprints(id) ON DELETE CASCADE,
                    branch_id UUID REFERENCES branches(id) ON DELETE CASCADE,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation_type TEXT,
                    PRIMARY KEY (id, branch_id)
                );
            """)

            # Create modified_files table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS modified_files (
                    blueprint_id UUID REFERENCES executable_blueprints(id) ON DELETE CASCADE,
                    branch_id UUID REFERENCES branches(id) ON DELETE CASCADE,
                    file_path TEXT NOT NULL,
                    content TEXT NOT NULL,
                    PRIMARY KEY (blueprint_id, branch_id, file_path)
                );
            """)

            # Create indexes
            cur.execute("CREATE INDEX IF NOT EXISTS idx_nodes_blueprint_branch ON executable_blueprint_nodes(blueprint_id, branch_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_edges_blueprint_branch ON executable_blueprint_edges(blueprint_id, branch_id);")
            
            conn.commit()
            print("Database schema successfully initialized.")
    except Exception as e:
        conn.rollback()
        print(f"Error initializing database: {e}")
        raise e
    finally:
        conn.close()
