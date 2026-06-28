import os
import uuid
import httpx
import tempfile
import shutil
import zipfile
from contextlib import asynccontextmanager
from typing import Optional, List
from fastapi import FastAPI, WebSocket, HTTPException, Query, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import config
from app.database import init_db, get_db_connection
from app.repositories.graph_repository import PostgresGraphRepository
from app.services.static_analysis_engine import StaticAnalysisEngine
from app.services.knowledge_graph_builder import KnowledgeGraphBuilder
from app.services.embedding_service import EmbeddingService
from app.services.inference_engine import InferenceEngine
from app.services.exporter import Exporter
from app.agents.graph import build_workflow
from supabase import create_client, Client
from e2b import Sandbox

# 1. Define lifespan for DB initialization
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
    except Exception as e:
        print(f"Lifespan DB initialization failed: {e}")
    yield

# 2. Setup FastAPI App
app = FastAPI(
    title="Genesis: Executable Engineering Blueprint Server",
    lifespan=lifespan
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://git-genesis.vercel.app",
        "https://git-genesis-five.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize singletons
graph_repo = PostgresGraphRepository()
embedding_svc = EmbeddingService()
inference_eng = InferenceEngine(graph_repo, embedding_svc)
static_analyzer = StaticAnalysisEngine()
kg_builder = KnowledgeGraphBuilder()

# Supabase Auth client for JWT verification
supabase_client: Client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)

def get_user_id_from_token(token: str) -> str:
    """Verifies Supabase JWT and returns the user's UUID string."""
    try:
        user_res = supabase_client.auth.get_user(token)
        if not user_res or not user_res.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return str(user_res.user.id)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid authorization token: {e}")

async def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split(" ")[1]
    return get_user_id_from_token(token)

def verify_blueprint_ownership(blueprint_id: str, user_id: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM executable_blueprints WHERE id = %s;", (blueprint_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Blueprint not found")
            if row["user_id"] and str(row["user_id"]) != user_id:
                raise HTTPException(status_code=403, detail="Permission denied to this blueprint")
    finally:
        conn.close()

# 3. Models
class AnalyzeRequest(BaseModel):
    url: str
    token: Optional[str] = None

class BranchCreateRequest(BaseModel):
    name: str

class RegenerateRequest(BaseModel):
    branch_id: str
    node_id: str
    updated_strategy: str

class EdgeCreateRequest(BaseModel):
    branch_id: str
    source_id: str
    target_id: str

class NodeCreateRequest(BaseModel):
    branch_id: str
    id: str
    name: str
    type: str
    summary: str

# 4. Helper to clone/fetch GitHub zip
def _clone_github_repo(repo_url: str, temp_dir: str, token: Optional[str] = None) -> str:
    """Downloads GitHub repository zip and extracts it to a local temporary folder."""
    # Convert github.com/user/repo to zip download URL
    url = repo_url.strip().rstrip("/")
    if not url.startswith("http"):
        url = "https://" + url
        
    # Extract owner and name
    pattern = r"github\.com/([^/]+)/([^/]+)"
    import re
    match = re.search(pattern, url)
    if not match:
        raise ValueError("Invalid GitHub URL format.")
    
    owner, name = match.group(1), match.group(2)
    # Strip .git if present
    if name.endswith(".git"):
        name = name[:-4]
        
    zip_url = f"https://github.com/{owner}/{name}/archive/refs/heads/main.zip"
    
    print(f"Downloading repository zip from {zip_url}...")
    headers = {}
    github_token = token or config.GITHUB_TOKEN
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    with httpx.Client(follow_redirects=True, timeout=30.0) as client:
        res = client.get(zip_url, headers=headers)
        # Fallback to master if main.zip fails
        if res.status_code != 200:
            zip_url = f"https://github.com/{owner}/{name}/archive/refs/heads/master.zip"
            res = client.get(zip_url, headers=headers)
            
        if res.status_code != 200:
            raise HTTPException(
                status_code=res.status_code, 
                detail=f"Failed to fetch zip for repo {owner}/{name}. Make sure it is public."
            )
            
        zip_path = os.path.join(temp_dir, "repo.zip")
        with open(zip_path, "wb") as f:
            f.write(res.content)
            
        # Extract
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
            
        # Locate extracted directory (usually repo-main or repo-master)
        extracted_dirs = [d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d)) and d != "__MACOSX"]
        if not extracted_dirs:
            raise FileNotFoundError("Could not find extracted repository folders.")
            
        return os.path.join(temp_dir, extracted_dirs[0])

# 5. Endpoints
@app.post("/api/blueprints/analyze")
async def analyze_repo(req: AnalyzeRequest, authorization: Optional[str] = Header(None)):
    """Sync endpoint to analyze a repository. Preferred to use WS /api/ws/analyze for real-time progress logs."""
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    elif req.token:
        token = req.token
        
    if not token:
        raise HTTPException(status_code=401, detail="Authentication token is required")
        
    user_id = get_user_id_from_token(token)
    
    temp_dir = tempfile.mkdtemp()
    conn = get_db_connection()
    try:
        # Resolve repository in database or create new
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO repositories (url, name, status, user_id)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (url, user_id) DO UPDATE SET status = 'Analyzing'
            RETURNING id;
        """, (req.url, os.path.basename(req.url), 'Analyzing', user_id))
        repo_id = cur.fetchone()['id']
        conn.commit()
        
        # Clone GitHub ZIP
        local_path = _clone_github_repo(req.url, temp_dir, req.token)
        
        # Static Analysis & KG Build
        facts = static_analyzer.analyze_repository(local_path)
        kg = kg_builder.build_knowledge_graph(facts)
        
        # Compile and execute LangGraph Multi-Agent Workflows
        workflow = build_workflow()
        initial_state = {
            "knowledge_graph": kg,
            "specialist_outputs": {},
            "blueprint_draft": {},
            "critic_feedback": [],
            "validator_result": {},
            "active_agent": "coordinator",
            "loop_count": 0,
            "logs": ["Init: Workspace compiled."]
        }
        
        final_state = workflow.invoke(initial_state)
        
        # Inference Engine merges and stores Executable Engineering Blueprint
        blueprint_id = str(uuid.uuid4())
        branch_id = inference_eng.persist_executable_blueprint(
            blueprint_id=blueprint_id,
            repository_id=repo_id,
            name=os.path.basename(req.url),
            agent_nodes=final_state["blueprint_draft"]["nodes"],
            agent_edges=final_state["blueprint_draft"]["edges"],
            user_id=user_id
        )
        
        # Mark repo status complete
        cur.execute("UPDATE repositories SET status = 'Completed' WHERE id = %s;", (repo_id,))
        conn.commit()
        
        return {
            "blueprint_id": blueprint_id,
            "branch_id": branch_id,
            "status": "success"
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
        shutil.rmtree(temp_dir, ignore_errors=True)

@app.websocket("/api/ws/analyze")
async def websocket_analyze(websocket: WebSocket):
    """Websocket route to run repository analysis and stream live agent debate logs to frontend."""
    await websocket.accept()
    temp_dir = tempfile.mkdtemp()
    conn = get_db_connection()
    try:
        # Receive URL
        data = await websocket.receive_json()
        repo_url = data.get("url")
        user_token = data.get("token")
        github_token = data.get("github_token")
        
        if not user_token:
            await websocket.send_json({"type": "error", "message": "Authentication token is missing. Please log in."})
            return
            
        try:
            user_id = get_user_id_from_token(user_token)
        except Exception as e:
            await websocket.send_json({"type": "error", "message": f"Authentication failed: {e}"})
            return

        if not repo_url:
            await websocket.send_json({"type": "error", "message": "Missing repository URL."})
            return
            
        await websocket.send_json({"type": "status", "message": "Checking repository database entry..."})
        
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO repositories (url, name, status, user_id)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (url, user_id) DO UPDATE SET status = 'Analyzing'
            RETURNING id;
        """, (repo_url, os.path.basename(repo_url), 'Analyzing', user_id))
        repo_id = cur.fetchone()['id']
        conn.commit()

        await websocket.send_json({"type": "status", "message": "Cloning GitHub repository zip content..."})
        local_path = _clone_github_repo(repo_url, temp_dir, github_token)

        await websocket.send_json({"type": "status", "message": "Running Static Analysis Engine (parsing AST files)..."})
        facts = static_analyzer.analyze_repository(local_path)
        
        await websocket.send_json({"type": "status", "message": "Building Unified Codebase Knowledge Graph..."})
        kg = kg_builder.build_knowledge_graph(facts)

        await websocket.send_json({"type": "status", "message": "Compiling multi-agent LangGraph orchestrator state..."})
        
        # Set up LangGraph loop listening for state logs
        workflow = build_workflow()
        state = {
            "knowledge_graph": kg,
            "specialist_outputs": {},
            "blueprint_draft": {},
            "critic_feedback": [],
            "validator_result": {},
            "active_agent": "coordinator",
            "loop_count": 0,
            "logs": ["Init: Workspace compiled."]
        }
        
        # Invoke workflow step by step so we can yield updates to WebSocket
        # To simulate step-by-step yield in WS, we execute and check logs size
        last_log_len = 0
        config_run = {"recursion_limit": 50}
        
        # Invoking workflow step-by-step to stream logs in real-time
        await websocket.send_json({"type": "status", "message": "Starting multi-agent debate and refinement loops..."})
        
        final_state = dict(state)
        last_logs = set()
        
        async for event in workflow.astream(state, config=config_run):
            for node_name, node_update in event.items():
                # Merge state updates in real-time
                for key, val in node_update.items():
                    if key == "logs":
                        from app.agents.graph import append_logs
                        final_state["logs"] = append_logs(final_state.get("logs", []), val)
                    elif key == "specialist_outputs":
                        from app.agents.graph import merge_specialist_outputs
                        final_state["specialist_outputs"] = merge_specialist_outputs(final_state.get("specialist_outputs", {}), val)
                    else:
                        final_state[key] = val
                
                # Stream any newly appended logs to frontend
                if "logs" in node_update:
                    for log in node_update["logs"]:
                        if log not in last_logs:
                            await websocket.send_json({"type": "log", "message": log})
                            last_logs.add(log)
                            import asyncio
                            await asyncio.sleep(0.02)

        await websocket.send_json({"type": "status", "message": "Invoking Inference Engine for final conflict resolution..."})
        
        blueprint_id = str(uuid.uuid4())
        branch_id = inference_eng.persist_executable_blueprint(
            blueprint_id=blueprint_id,
            repository_id=repo_id,
            name=os.path.basename(repo_url),
            agent_nodes=final_state["blueprint_draft"]["nodes"],
            agent_edges=final_state["blueprint_draft"]["edges"],
            user_id=user_id
        )

        cur.execute("UPDATE repositories SET status = 'Completed' WHERE id = %s;", (repo_id,))
        conn.commit()

        await websocket.send_json({
            "type": "completed", 
            "blueprint_id": blueprint_id,
            "branch_id": branch_id
        })
    except Exception as e:
        conn.rollback()
        await websocket.send_json({"type": "error", "message": str(e)})
    finally:
        conn.close()
        shutil.rmtree(temp_dir, ignore_errors=True)
        await websocket.close()

@app.get("/api/blueprints/{id}/branches")
async def get_blueprint_branches(id: str, user_id: str = Depends(get_current_user_id)):
    """Lists all branch variants for a blueprint."""
    verify_blueprint_ownership(id, user_id)
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, blueprint_id, name, active, created_at FROM branches
                WHERE blueprint_id = %s;
            """, (id,))
            return cur.fetchall()
    finally:
        conn.close()

@app.post("/api/blueprints/{id}/branches")
async def create_blueprint_branch(id: str, req: BranchCreateRequest, user_id: str = Depends(get_current_user_id)):
    """Creates a new branch variant by copying nodes from active branch."""
    verify_blueprint_ownership(id, user_id)
    conn = get_db_connection()
    try:
        # Get active branch first
        active = graph_repo.get_active_branch(id)
        if not active:
            raise HTTPException(status_code=404, detail="No active branch found to copy.")
            
        new_branch_id = str(uuid.uuid4())
        graph_repo.clone_branch(active["id"], new_branch_id, req.name)
        return {
            "branch_id": new_branch_id,
            "name": req.name,
            "status": "cloned"
        }
    finally:
        conn.close()

@app.post("/api/blueprints/{id}/activate-branch/{branch_id}")
async def activate_blueprint_branch(id: str, branch_id: str, user_id: str = Depends(get_current_user_id)):
    """Switches active branch for the blueprint."""
    verify_blueprint_ownership(id, user_id)
    try:
        graph_repo.set_active_branch(id, branch_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/blueprints/{id}/data")
async def get_blueprint_graph_data(id: str, branch_id: Optional[str] = Query(None), user_id: str = Depends(get_current_user_id)):
    """Retrieves nodes and edges for the specified blueprint branch."""
    target_branch = branch_id
    if not target_branch:
        active = graph_repo.get_active_branch(id)
        if not active:
            raise HTTPException(status_code=404, detail="No active branch found.")
        target_branch = active["id"]

    nodes = graph_repo.get_nodes(id, target_branch)
    edges = graph_repo.get_edges(id, target_branch)
    
    return {
        "nodes": nodes,
        "edges": edges,
        "branch_id": target_branch
    }

@app.get("/api/blueprints/{id}/search")
async def search_blueprint_nodes(
    id: str,
    q: str = Query(...),
    branch_id: Optional[str] = Query(None),
    user_id: str = Depends(get_current_user_id)
):
    """Performs a semantic vector similarity search on the nodes of a blueprint branch."""
    verify_blueprint_ownership(id, user_id)
    
    target_branch = branch_id
    if not target_branch:
        active = graph_repo.get_active_branch(id)
        if not active:
            raise HTTPException(status_code=404, detail="No active branch found.")
        target_branch = active["id"]

    query_embedding = embedding_svc.get_embedding(q)
    results = graph_repo.vector_search_nodes(id, target_branch, query_embedding, limit=5)
    
    return {
        "query": q,
        "results": [
            {
                "id": node["id"],
                "name": node["name"],
                "type": node["type"],
                "distance": node.get("distance", 1.0),
                "architectural_reasoning_summary": node["architectural_reasoning_summary"]
            }
            for node in results
        ]
    }

@app.post("/api/blueprints/{id}/regenerate")
async def regenerate_blueprint_nodes(
    id: str, 
    req: RegenerateRequest,
    authorization: Optional[str] = Header(None),
    x_github_token: Optional[str] = Header(None)
):
    """Regenerates a node and all downstream descendants with a self-healing sandbox coding compile check, streaming progress logs."""
    from fastapi.responses import StreamingResponse
    import sys
    import json
    import asyncio

    async def event_generator():
        # Setup temporary directories
        temp_dir = tempfile.mkdtemp()
        try:
            yield f"data: {json.dumps({'type': 'log', 'message': 'Sandbox: Initializing folder...'})}\n\n"
            await asyncio.sleep(0.05)
            
            # Authenticate the user
            if not authorization or not authorization.startswith("Bearer "):
                yield f"data: {json.dumps({'type': 'error', 'message': 'Missing or invalid Authorization header.'})}\n\n"
                return
            token = authorization.split(" ")[1]
            try:
                user_id = get_user_id_from_token(token)
                verify_blueprint_ownership(id, user_id)
            except Exception as auth_err:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Authentication/Authorization failed: {auth_err}'})}\n\n"
                return
            
            # 1. Fetch target repository URL
            conn = get_db_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT r.url FROM executable_blueprints b
                        JOIN repositories r ON b.repository_id = r.id
                        WHERE b.id = %s;
                    """, (id,))
                    row = cur.fetchone()
                    if not row:
                        yield f"data: {json.dumps({'type': 'error', 'message': 'Blueprint repository not found.'})}\n\n"
                        return
                    repo_url = row["url"]
            finally:
                conn.close()

            yield f"data: {json.dumps({'type': 'log', 'message': f'Sandbox: Selected repository {repo_url} for self-healing verification.'})}\n\n"
            await asyncio.sleep(0.05)
            
            node = graph_repo.get_node(req.node_id, req.branch_id)
            if not node:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Node not found.'})}\n\n"
                return

            node_name = node.get("name", "Unknown")
            yield f"data: {json.dumps({'type': 'log', 'message': f'Sandbox: Selected node {node_name} for regeneration.'})}\n\n"
            await asyncio.sleep(0.05)

            # Resolve paths
            source_paths = node.get("source_files")
            if isinstance(source_paths, str):
                try:
                    source_paths = json.loads(source_paths)
                except:
                    source_paths = [source_paths]
            elif not isinstance(source_paths, list):
                source_paths = []

            # 3. Invoke self-healing Code Modification loops (up to 3 iterations)
            from app.agents.specialists.code_modifier import code_modifier_node
            
            state = {
                "knowledge_graph": {},
                "logs": ["Init: Sandbox alignment started."],
                "current_node_id": req.node_id,
                "strategy_override": req.updated_strategy,
                "source_files": {}
            }
            
            yield f"data: {json.dumps({'type': 'log', 'message': 'Sandbox: Fetching original source file contents from GitHub...'})}\n\n"
            local_path = _clone_github_repo(repo_url, temp_dir, x_github_token)
            
            source_files = {}
            for path in source_paths:
                full_path = os.path.join(local_path, path.strip().lstrip("/"))
                if os.path.exists(full_path) and os.path.isfile(full_path):
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        source_files[path] = f.read()
            state["source_files"] = source_files
            
            success = False
            compilation_error = None
            modifications = []
            
            for iteration in range(3):
                yield f"data: {json.dumps({'type': 'log', 'message': f'Self-Healing: Iteration {iteration+1}/3 started using Groq Llama-3.3-70b...'})}\n\n"
                await asyncio.sleep(0.05)
                if compilation_error:
                    state["strategy_override"] = f"""{req.updated_strategy}
                    
                    CRITICAL WARNING: The previous attempt failed to compile/build with this error:
                    {compilation_error}
                    
                    Please fix the syntax, correct references, and resolve compilation errors in your modifications."""

                result = code_modifier_node(state)
                modifications = result.get("modifications", [])
                
                if not modifications:
                    yield f"data: {json.dumps({'type': 'log', 'message': 'Self-Healing: No modifications generated (using regex fallback or API failed).'})}\n\n"
                else:
                    for mod in modifications:
                        mod_file_path = mod["file_path"]
                        yield f"data: {json.dumps({'type': 'log', 'message': f'Self-Healing: Applying changes to {mod_file_path}...'})}\n\n"
                await asyncio.sleep(0.05)

                # Syntax Compile & Unit Test Check using E2B Sandbox
                compilation_error = None
                
                yield f"data: {json.dumps({'type': 'log', 'message': 'E2B Sandbox: Initializing remote cloud sandbox VM...'})}\n\n"
                await asyncio.sleep(0.01)
                
                try:
                    e2b_sandbox = Sandbox.create()
                    
                    # 1. Clone repository inside E2B sandbox
                    yield f"data: {json.dumps({'type': 'log', 'message': 'E2B Sandbox: Cloning repository inside the cloud VM...'})}\n\n"
                    clone_url = repo_url
                    github_token = x_github_token or config.GITHUB_TOKEN
                    if github_token:
                        # Authenticate clone url
                        clone_url = clone_url.replace("https://", f"https://x-access-token:{github_token}@")
                        
                    clone_res = e2b_sandbox.commands.run(f"git clone {clone_url} /home/user/workspace")
                    if clone_res.exit_code != 0:
                        yield f"data: {json.dumps({'type': 'log', 'message': f'E2B Sandbox Warning: Git clone failed in sandbox ({clone_res.stderr.strip()}). Uploading files manually...'})}\n\n"
                        # Fallback: create directory and upload files manually
                        e2b_sandbox.commands.run("mkdir -p /home/user/workspace")
                        for f_path, f_content in source_files.items():
                            dir_to_make = os.path.dirname(f_path).strip().lstrip("/")
                            if dir_to_make:
                                e2b_sandbox.commands.run(f"mkdir -p /home/user/workspace/{dir_to_make}")
                            e2b_sandbox.files.write(f"/home/user/workspace/{f_path}", f_content)
                    
                    # Install dependencies if present
                    if e2b_sandbox.files.exists("/home/user/workspace/requirements.txt"):
                        yield f"data: {json.dumps({'type': 'log', 'message': 'E2B Sandbox: Installing Python dependencies inside sandbox...'})}\n\n"
                        e2b_sandbox.commands.run("pip3 install -r /home/user/workspace/requirements.txt", timeout=45)
                    elif e2b_sandbox.files.exists("/home/user/workspace/package.json"):
                        yield f"data: {json.dumps({'type': 'log', 'message': 'E2B Sandbox: Installing Node dependencies inside sandbox...'})}\n\n"
                        e2b_sandbox.commands.run("cd /home/user/workspace && npm install", timeout=60)
                        
                    # Apply edits to files in E2B sandbox
                    for mod in modifications:
                        file_path = mod["file_path"]
                        content = mod["content"]
                        sandbox_file_path = f"/home/user/workspace/{file_path.strip().lstrip('/')}"
                        # Ensure parent dir exists
                        dir_to_make = os.path.dirname(file_path).strip().lstrip("/")
                        if dir_to_make:
                            e2b_sandbox.commands.run(f"mkdir -p /home/user/workspace/{dir_to_make}")
                        e2b_sandbox.files.write(sandbox_file_path, content)
                        
                    # 2. Syntax Compile Check
                    yield f"data: {json.dumps({'type': 'log', 'message': 'E2B Sandbox: Running remote syntax check compilation...'})}\n\n"
                    for mod in modifications:
                        file_path = mod["file_path"]
                        sandbox_file_path = f"/home/user/workspace/{file_path.strip().lstrip('/')}"
                        if file_path.endswith(".py"):
                            res = e2b_sandbox.commands.run(f"python3 -m py_compile {sandbox_file_path}")
                            if res.exit_code != 0:
                                compilation_error = f"Python syntax check failed for {file_path}:\n{res.stderr or res.stdout}"
                                break
                        elif file_path.endswith(".js") or file_path.endswith(".jsx") or file_path.endswith(".ts") or file_path.endswith(".tsx"):
                            # Use esbuild to parse and check syntax, redirecting stdout to /dev/null
                            res = e2b_sandbox.commands.run(f"npx --yes esbuild {sandbox_file_path} > /dev/null")
                            if res.exit_code != 0:
                                compilation_error = f"JavaScript/TypeScript syntax check failed for {file_path}:\n{res.stderr or res.stdout}"
                                break
                                
                    # 3. Unit Test Check
                    if not compilation_error:
                        test_ran = False
                        test_error = None
                        if any(f.endswith(".py") for f in source_files.keys()) and e2b_sandbox.files.exists("/home/user/workspace/tests"):
                            yield f"data: {json.dumps({'type': 'log', 'message': 'E2B Sandbox: Python tests directory detected. Running pytest inside VM...'})}\n\n"
                            res = e2b_sandbox.commands.run("cd /home/user/workspace && pytest -v", timeout=20.0)
                            test_ran = True
                            if res.exit_code != 0:
                                test_error = f"pytest failure:\n{res.stdout or res.stderr}"
                        elif e2b_sandbox.files.exists("/home/user/workspace/package.json"):
                            yield f"data: {json.dumps({'type': 'log', 'message': 'E2B Sandbox: Node.js package.json detected. Running npm test inside VM...'})}\n\n"
                            res = e2b_sandbox.commands.run("cd /home/user/workspace && npm test", timeout=30.0)
                            test_ran = True
                            if res.exit_code != 0:
                                test_error = f"npm test failure:\n{res.stdout or res.stderr}"
                                
                        if test_ran and test_error:
                            compilation_error = test_error
                            yield f"data: {json.dumps({'type': 'log', 'message': 'E2B Sandbox: Test failures detected: ' + str(test_error)})}\n\n"
                    
                    # Kill sandbox
                    e2b_sandbox.kill()
                    
                except Exception as sandbox_err:
                    compilation_error = f"E2B Sandbox execution failed: {sandbox_err}"
                    yield f"data: {json.dumps({'type': 'log', 'message': f'E2B Sandbox Error: {sandbox_err}'})}\n\n"

                if not compilation_error:
                    success = True
                    yield f"data: {json.dumps({'type': 'log', 'message': 'Self-Healing Success: All modifications successfully validated on Iteration ' + str(iteration+1) + '!'})}\n\n"
                    break
                else:
                    yield f"data: {json.dumps({'type': 'log', 'message': 'Self-Healing Error (Iteration ' + str(iteration+1) + '): ' + str(compilation_error)})}\n\n"
                await asyncio.sleep(0.05)

            # Save latest modifications
            for mod in modifications:
                graph_repo.save_modified_file(id, req.branch_id, mod["file_path"], mod["content"])

            # 4. Generate updated prompt using Groq (Llama-3.3)
            yield f"data: {json.dumps({'type': 'log', 'message': 'Groq Planner: Re-writing task instruction prompts...'})}\n\n"
            planner_prompt = f"""
            You are the Blueprint Planner Agent.
            The user has overridden the architecture strategy for Node '{req.node_id}' with:
            "{req.updated_strategy}"
            
            The current generated task instructions are:
            "{node.get('generated_task', '')}"
            
            Rewrite the coding instructions/prompts for this node to implement the new strategy.
            Be detailed, explain how to structure the edits, and provide solid guidance.
            Keep the response as clean instruction text.
            """
            
            new_task = ""
            if config.GROQ_API_KEY:
                try:
                    url = "https://api.groq.com/openai/v1/chat/completions"
                    headers = {
                        "Authorization": f"Bearer {config.GROQ_API_KEY}",
                        "content-type": "application/json"
                    }
                    payload = {
                        "model": config.MODEL_PLANNER,
                        "messages": [{"role": "user", "content": planner_prompt}],
                        "temperature": 0.2
                    }
                    async with httpx.AsyncClient(timeout=20.0) as client:
                        res = await client.post(url, json=payload)
                        if res.status_code == 200:
                            new_task = res.json()["choices"][0]["message"]["content"]
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'log', 'message': f'Groq Planner Warning: API call failed ({e}). Using fallback.'})}\n\n"

            if not new_task:
                new_task = f"[REGENERATED STRATEGY]: {req.updated_strategy}\n\n{node.get('generated_task', '')}"

            graph_repo.update_node(
                req.node_id,
                req.branch_id,
                generated_task=new_task,
                confidence_score=99
            )

            # 5. Align downstream nodes (using Recursive CTE)
            descendants = graph_repo.get_descendants(id, req.branch_id, req.node_id)
            yield f"data: {json.dumps({'type': 'log', 'message': f'Groq Planner: Aligning {len(descendants)} downstream dependent modules...'})}\n\n"
            
            for desc_id in descendants:
                desc_node = graph_repo.get_node(desc_id, req.branch_id)
                if not desc_node:
                    continue

                desc_prompt = f"""
                You are the Blueprint Planner Agent.
                An upstream prerequisite module (Node '{req.node_id}') was updated to use this new strategy:
                "{req.updated_strategy}"
                
                This downstream node '{desc_id}' depends on it. 
                The current downstream task instructions are:
                "{desc_node.get('generated_task', '')}"
                
                Align the downstream task instructions to integrate cleanly with the upstream database/logic shift.
                Be detailed and print the updated task instructions.
                """

                desc_task = ""
                if config.GROQ_API_KEY:
                    try:
                        url = "https://api.groq.com/openai/v1/chat/completions"
                        headers = {
                            "Authorization": f"Bearer {config.GROQ_API_KEY}",
                            "content-type": "application/json"
                        }
                        payload = {
                            "model": config.MODEL_PLANNER,
                            "messages": [{"role": "user", "content": desc_prompt}],
                            "temperature": 0.2
                        }
                        async with httpx.AsyncClient(timeout=20.0) as client:
                            res = await client.post(url, json=payload)
                            if res.status_code == 200:
                                desc_task = res.json()["choices"][0]["message"]["content"]
                    except Exception as e:
                        pass

                if not desc_task:
                    desc_task = f"""[PARENT STRATEGY UPDATED ({req.node_id})]: Downstream alignment applied.
{desc_node.get('generated_task', '')}"""

                graph_repo.update_node(desc_id, req.branch_id, generated_task=desc_task)

            yield f"data: {json.dumps({'type': 'completed', 'regenerated_count': len(descendants) + 1, 'descendants_affected': descendants})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Regeneration process failed: {str(e)}'})}\n\n"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/api/blueprints/{id}/edges")
async def add_custom_edge(id: str, req: EdgeCreateRequest, user_id: str = Depends(get_current_user_id)):
    """Adds a custom dependency edge to the blueprint graph."""
    verify_blueprint_ownership(id, user_id)
    edge_id = f"edge_{uuid.uuid4().hex[:6]}"
    try:
        graph_repo.add_edge(edge_id, id, req.branch_id, req.source_id, req.target_id, "custom")
        return {"status": "success", "edge_id": edge_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/blueprints/{id}/edges/{edge_id}")
async def delete_custom_edge(id: str, edge_id: str, branch_id: str = Query(...), user_id: str = Depends(get_current_user_id)):
    """Deletes a custom dependency edge from the blueprint graph."""
    verify_blueprint_ownership(id, user_id)
    try:
        graph_repo.delete_edge(edge_id, branch_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/blueprints/{id}/nodes")
async def add_custom_node(id: str, req: NodeCreateRequest, user_id: str = Depends(get_current_user_id)):
    """Creates a custom blueprint task node."""
    verify_blueprint_ownership(id, user_id)
    try:
        existing = graph_repo.get_node(req.id, req.branch_id)
        if existing:
            raise HTTPException(status_code=400, detail="Node ID already exists.")
            
        graph_repo.add_node(
            node_id=req.id,
            blueprint_id=id,
            branch_id=req.branch_id,
            name=req.name,
            node_type=req.type,
            confidence_score=100,
            supporting_evidence=[],
            architectural_reasoning_summary=req.summary,
            source_files=[],
            dependency_references=[],
            related_modules=[],
            generated_task=f"[CUSTOM NODE]: Implement {req.name}.\n\nInstructions:\n{req.summary}",
            status="todo"
        )
        return {"status": "success", "node_id": req.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/blueprints/{id}/nodes/{node_id}")
async def delete_custom_node(id: str, node_id: str, branch_id: str = Query(...), user_id: str = Depends(get_current_user_id)):
    """Deletes a custom task node and all associated connections."""
    verify_blueprint_ownership(id, user_id)
    try:
        graph_repo.delete_node(node_id, branch_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/blueprints/compare")
async def compare_blueprints(branch1: str, branch2: str, user_id: str = Depends(get_current_user_id)):
    """Compares two blueprints or branch variants, highlighting structural divergence."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Verify ownership of both branches
            cur.execute("SELECT blueprint_id FROM branches WHERE id = %s;", (branch1,))
            row1 = cur.fetchone()
            if not row1:
                raise HTTPException(status_code=404, detail="Branch 1 not found")
                
            cur.execute("SELECT blueprint_id FROM branches WHERE id = %s;", (branch2,))
            row2 = cur.fetchone()
            if not row2:
                raise HTTPException(status_code=404, detail="Branch 2 not found")
                
            verify_blueprint_ownership(row1["blueprint_id"], user_id)
            verify_blueprint_ownership(row2["blueprint_id"], user_id)

            # Fetch nodes from branch 1
            cur.execute("SELECT id, name, type, confidence_score, generated_task FROM executable_blueprint_nodes WHERE branch_id = %s;", (branch1,))
            nodes1 = {n['id']: n for n in cur.fetchall()}
            
            # Fetch nodes from branch 2
            cur.execute("SELECT id, name, type, confidence_score, generated_task FROM executable_blueprint_nodes WHERE branch_id = %s;", (branch2,))
            nodes2 = {n['id']: n for n in cur.fetchall()}

        # Highlight differences
        divergent_nodes = []
        for nid in set(list(nodes1.keys()) + list(nodes2.keys())):
            n1 = nodes1.get(nid)
            n2 = nodes2.get(nid)
            
            if not n1:
                divergent_nodes.append({"id": nid, "status": "added_in_branch2", "node": n2})
            elif not n2:
                divergent_nodes.append({"id": nid, "status": "removed_in_branch2", "node": n1})
            else:
                # Compare fields
                diffs = []
                if n1["generated_task"] != n2["generated_task"]:
                    diffs.append("generated_task")
                if n1["confidence_score"] != n2["confidence_score"]:
                    diffs.append("confidence_score")
                    
                if diffs:
                    divergent_nodes.append({
                        "id": nid,
                        "status": "modified",
                        "changes": diffs,
                        "branch1_node": n1,
                        "branch2_node": n2
                    })

        return {
            "divergent_nodes": divergent_nodes,
            "match_rate": (1.0 - (len(divergent_nodes) / max(1, len(nodes1) + len(nodes2)))) * 100
        }
    finally:
        conn.close()

@app.get("/api/blueprints/{id}/export")
async def export_blueprint_artifact(id: str, branch_id: str, format: str = "json", user_id: str = Depends(get_current_user_id)):
    """Generates and downloads the Executable Engineering Blueprint in the chosen format."""
    verify_blueprint_ownership(id, user_id)
    nodes = graph_repo.get_nodes(id, branch_id)
    edges = graph_repo.get_edges(id, branch_id)
    
    if not nodes:
        raise HTTPException(status_code=404, detail="No nodes found for this blueprint branch.")

    try:
        exported_str = Exporter.export_blueprint(nodes, edges, format)
        return {
            "format": format,
            "filename": f"executable_blueprint_{branch_id}.{format if format in ('json', 'markdown') else 'txt'}",
            "content": exported_str
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/blueprints/{id}/file-content")
async def get_blueprint_file_content(
    id: str, 
    path: str = Query(...),
    authorization: Optional[str] = Header(None),
    x_github_token: Optional[str] = Header(None)
):
    """Fetches the raw content of a file in the blueprint repository from GitHub."""
    token = authorization.split(" ")[1] if authorization and authorization.startswith("Bearer ") else None
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    user_id = get_user_id_from_token(token)
    verify_blueprint_ownership(id, user_id)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT r.url FROM executable_blueprints b
                JOIN repositories r ON b.repository_id = r.id
                WHERE b.id = %s;
            """, (id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Blueprint or repository not found.")
            repo_url = row["url"]
    finally:
        conn.close()

    # Parse owner and name
    url = repo_url.strip().rstrip("/")
    if not url.startswith("http"):
        url = "https://" + url
    
    import re
    pattern = r"github\.com/([^/]+)/([^/]+)"
    match = re.search(pattern, url)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid GitHub repository URL.")
    
    owner, name = match.group(1), match.group(2)
    if name.endswith(".git"):
        name = name[:-4]

    # Clean path (ensure no leading slashes)
    clean_path = path.strip().lstrip("/")

    # Try main branch first
    headers = {}
    github_token = x_github_token or config.GITHUB_TOKEN
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    with httpx.Client(follow_redirects=True, timeout=10.0) as client:
        # Try main branch
        raw_url = f"https://raw.githubusercontent.com/{owner}/{name}/main/{clean_path}"
        res = client.get(raw_url, headers=headers)
        if res.status_code != 200:
            # Try master branch fallback
            raw_url = f"https://raw.githubusercontent.com/{owner}/{name}/master/{clean_path}"
            res = client.get(raw_url, headers=headers)
            
        if res.status_code != 200:
            raise HTTPException(status_code=404, detail=f"File {clean_path} not found in main or master branches.")
            
        return {
            "path": clean_path,
            "content": res.text
        }

@app.get("/api/blueprints/{id}/modified-files")
async def get_modified_files(id: str, branch_id: str = Query(...), user_id: str = Depends(get_current_user_id)):
    """Fetches all modified files for the specified blueprint branch."""
    verify_blueprint_ownership(id, user_id)
    try:
        files = graph_repo.get_modified_files(id, branch_id)
        return files
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class NodeStatusUpdateRequest(BaseModel):
    status: str

@app.post("/api/blueprints/{id}/branches/{branch_id}/nodes/{node_id}/status")
async def update_node_status(id: str, branch_id: str, node_id: str, req: NodeStatusUpdateRequest, user_id: str = Depends(get_current_user_id)):
    """Updates the status (todo, in_progress, done) of a node."""
    verify_blueprint_ownership(id, user_id)
    if req.status not in ('todo', 'in_progress', 'done'):
        raise HTTPException(status_code=400, detail="Invalid status value. Must be 'todo', 'in_progress', or 'done'.")
    try:
        graph_repo.update_node(node_id, branch_id, status=req.status)
        return {"status": "success", "node_id": node_id, "new_status": req.status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class CommitRequest(BaseModel):
    branch_id: str

@app.post("/api/blueprints/{id}/commit")
async def commit_blueprint_to_github(
    id: str, 
    req: CommitRequest,
    authorization: Optional[str] = Header(None),
    x_github_token: Optional[str] = Header(None)
):
    """Commits compiled blueprint instructions and Cursor rules directly to the GitHub repository as a PR."""
    token = authorization.split(" ")[1] if authorization and authorization.startswith("Bearer ") else None
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    user_id = get_user_id_from_token(token)
    verify_blueprint_ownership(id, user_id)
    
    import base64
    github_token = x_github_token or config.GITHUB_TOKEN
    if not github_token:
        raise HTTPException(status_code=400, detail="Missing GitHub Personal Access Token (PAT). Please set it in Settings.")
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT r.url FROM executable_blueprints b
                JOIN repositories r ON b.repository_id = r.id
                WHERE b.id = %s;
            """, (id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Blueprint repository not found.")
            repo_url = row["url"]
    finally:
        conn.close()

    # Parse owner/name
    url = repo_url.strip().rstrip("/")
    if not url.startswith("http"):
        url = "https://" + url
    
    import re
    pattern = r"github\.com/([^/]+)/([^/]+)"
    match = re.search(pattern, url)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid GitHub repository URL.")
    
    owner, name = match.group(1), match.group(2)
    if name.endswith(".git"):
        name = name[:-4]

    # Fetch nodes and edges to compile contents
    nodes = graph_repo.get_nodes(id, req.branch_id)
    edges = graph_repo.get_edges(id, req.branch_id)
    if not nodes:
        raise HTTPException(status_code=404, detail="No nodes found to export.")

    cursor_rules_content = Exporter.export_blueprint(nodes, edges, "cursor")
    blueprint_md_content = Exporter.export_blueprint(nodes, edges, "markdown")

    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Step 1: Detect base branch (main/master)
    base_branch = "main"
    async with httpx.AsyncClient(timeout=15.0) as client:
        # Check main ref
        res = await client.get(f"https://api.github.com/repos/{owner}/{name}/git/ref/heads/main", headers=headers)
        if res.status_code != 200:
            res = await client.get(f"https://api.github.com/repos/{owner}/{name}/git/ref/heads/master", headers=headers)
            if res.status_code == 200:
                base_branch = "master"
            else:
                raise HTTPException(status_code=res.status_code, detail="Could not retrieve default branch SHA from GitHub.")
        
        base_sha = res.json()["object"]["sha"]

        # Step 2: Create a unique branch name
        new_branch_name = f"gitgenesis-blueprint-{uuid.uuid4().hex[:6]}"
        create_ref_payload = {
            "ref": f"refs/heads/{new_branch_name}",
            "sha": base_sha
        }
        res = await client.post(f"https://api.github.com/repos/{owner}/{name}/git/refs", json=create_ref_payload, headers=headers)
        if res.status_code not in (200, 201):
            raise HTTPException(status_code=res.status_code, detail="Failed to create new variant branch on GitHub.")

        # Helper function to write file content to the branch
        async def _write_github_file(path: str, content: str, message: str):
            encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
            
            # Check if file already exists to get its SHA
            file_sha = None
            check_res = await client.get(
                f"https://api.github.com/repos/{owner}/{name}/contents/{path}?ref={new_branch_name}",
                headers=headers
            )
            if check_res.status_code == 200:
                file_sha = check_res.json()["sha"]

            payload = {
                "message": message,
                "content": encoded,
                "branch": new_branch_name
            }
            if file_sha:
                payload["sha"] = file_sha

            await client.put(
                f"https://api.github.com/repos/{owner}/{name}/contents/{path}",
                json=payload,
                headers=headers
            )

        # Step 3: Write .cursorrules, .genesis/blueprint.md, and all sandboxed code modifications
        await _write_github_file(".cursorrules", cursor_rules_content, "Add Cursor rules instructions")
        await _write_github_file(".genesis/blueprint.md", blueprint_md_content, "Add GitGenesis engineering checklist blueprint")

        # Write modified files if any exist in this variant branch
        modified_files = graph_repo.get_modified_files(id, req.branch_id)
        for m_file in modified_files:
            path = m_file["file_path"]
            content = m_file["content"]
            await _write_github_file(path, content, f"Refactor {os.path.basename(path)} to align with blueprint strategies")

        # Step 4: Create Pull Request
        pr_payload = {
            "title": "Add GitGenesis Engineering Blueprint & Cursor Rules",
            "body": """This Pull Request introduces the Executable Engineering Blueprint generated by GitGenesis.

### 📋 What is added:
1. **`.cursorrules`**: Tailored task execution rules for Cursor IDE.
2. **`.genesis/blueprint.md`**: A detailed, step-by-step codebase walkthrough and dependency checklist.

*Generated by GitGenesis by Nevan.*""",
            "head": new_branch_name,
            "base": base_branch
        }
        
        pr_res = await client.post(f"https://api.github.com/repos/{owner}/{name}/pulls", json=pr_payload, headers=headers)
        if pr_res.status_code not in (200, 201):
            # If PR fails, return the branch URL directly
            return {
                "status": "branch_created",
                "branch": new_branch_name,
                "url": f"https://github.com/{owner}/{name}/tree/{new_branch_name}",
                "detail": "Branch created successfully. Pull Request initialization skipped."
            }

        pr_data = pr_res.json()
        return {
            "status": "pr_created",
            "branch": new_branch_name,
            "url": pr_data["html_url"],
            "number": pr_data["number"]
        }
