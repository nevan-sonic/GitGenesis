import httpx
import json
from typing import Dict, Any, List
from app.config import config

def planner_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Blueprint Planner Agent: Synthesizes specialist inputs and drafts the Executable Engineering Blueprint graph."""
    kg = state.get("knowledge_graph") or {}
    specialist_outputs = state.get("specialist_outputs") or {}
    logs = state.get("logs") or []
    critic_feedback = state.get("critic_feedback") or []
    
    logs.append("Blueprint Planner: Synthesizing reports and drafting Executable Engineering Blueprint...")

    prompt = f"""
    You are the Blueprint Planner Agent.
    Based on the following reports and facts:
    Specialists reports: {list(specialist_outputs.values())}
    Knowledge Graph Modules: {list(kg.get("modules", {}).keys())}
    Critic Feedback: {critic_feedback}
    
    Construct an Executable Engineering Blueprint.
    The response MUST be a valid JSON containing "nodes" and "edges" keys:
    - Nodes list with fields: id, name, type (e.g. foundation, database, middleware, api, frontend), confidence_score (an integer between 0 and 100, representing percentage), confidence_explanation (a short string explaining why you gave it this percentage score based on source code files or architecture rules), supporting_evidence (list of files), architectural_reasoning_summary, source_files, dependency_references, related_modules, generated_task.
    - Edges list with fields: source, target, relation_type.
    
    CRITICAL RULES:
    1. Do NOT create database nodes (e.g. 'PostgreSQL', 'Database Layer') unless you see clear evidence of database driver packages (e.g., pg, pg-promise, mongoose, psycopg2, prisma, sqlite3) or database schema/migration/connection files in the 'Knowledge Graph Modules' or 'Specialist reports'. If the project does not use a database, do NOT construct a database node.
    2. Only list files in 'supporting_evidence' and 'source_files' that are actually present in the 'Knowledge Graph Modules' list. Do NOT invent/hallucinate files or list unrelated files (e.g., listing 'next-env.d.ts' or config files as evidence for a database or middleware task).
    3. Ensure the names, tasks, and file associations are highly accurate and directly match the actual technologies used in the repository.

    Ensure the JSON is well-formed.
    """

    blueprint_draft = {}
    if config.GROQ_API_KEY:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {config.GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            # Groq model expects response_format for json
            payload = {
                "model": config.DEFAULT_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.0
            }
            with httpx.Client(timeout=20.0) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    text = res.json()["choices"][0]["message"]["content"]
                    blueprint_draft = json.loads(text)
        except Exception as e:
            print(f"Blueprint Planner API call failed: {e}")
            
    # Deterministic fallback draft if LLM fails
    if not blueprint_draft or not blueprint_draft.get("nodes"):
        layers = kg.get("layers", {})
        nodes = []
        edges = []
        
        # Build logical nodes based on detected layers
        ordered_layers = ["Utilities", "Database", "Middleware", "Routing/API", "Frontend UI", "Other"]
        prev_node_id = None
        
        for layer_name in ordered_layers:
            files = layers.get(layer_name, [])
            if not files:
                continue
                
            node_id = layer_name.lower().replace("/", "_").replace(" ", "_")
            
            # Simple AI task prompt
            generated_task = f"""
Implement the {layer_name} Layer components.
Source modules to reference/build:
{chr(10).join(['- ' + f for f in files])}

Ensure standard coding patterns, proper error boundaries, and integration with upstream dependencies.
"""
            
            nodes.append({
                "id": node_id,
                "name": f"{layer_name} Layer",
                "type": "layer",
                "confidence_score": 95,
                "confidence_explanation": f"95% confidence because there are {len(files)} source modules matched under the {layer_name} directory structure.",
                "supporting_evidence": files[:3],
                "architectural_reasoning_summary": f"Grouped {len(files)} files belonging to the {layer_name} component category of the application.",
                "source_files": files,
                "dependency_references": [prev_node_id] if prev_node_id else [],
                "related_modules": files,
                "generated_task": generated_task
            })
            
            # Construct sequential dependency edges
            if prev_node_id:
                edges.append({
                    "source": prev_node_id,
                    "target": node_id,
                    "relation_type": "DEPENDS_ON"
                })
            prev_node_id = node_id
            
        blueprint_draft = {
            "nodes": nodes,
            "edges": edges
        }

    logs.append(f"Blueprint Planner: Blueprint draft created with {len(blueprint_draft.get('nodes', []))} nodes and {len(blueprint_draft.get('edges', []))} edges.")
    
    return {
        "blueprint_draft": blueprint_draft,
        "logs": logs,
        "active_agent": "coordinator"  # Always route back to coordinator
    }
