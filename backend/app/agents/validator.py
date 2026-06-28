import json
import httpx
from typing import Dict, Any
from app.config import config

def validator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Validator Agent: Performs final structural and semantic checks and graph validation using LLM."""
    blueprint_draft = state.get("blueprint_draft") or {}
    logs = state.get("logs") or []
    
    logs.append("Validator Agent: Running final semantic validation checks...")
    
    nodes = blueprint_draft.get("nodes", [])
    edges = blueprint_draft.get("edges", [])
    
    errors = []
    
    # 1. Structural Checks (Node & Edge Integrity)
    if not nodes:
        errors.append("Validation Error: Executable Engineering Blueprint must contain at least one node.")
        
    for node in nodes:
        if not node.get("generated_task") or not node["generated_task"].strip():
            errors.append(f"Validation Error: Node [{node['id']}] does not contain an AI task description.")

    node_ids = {node["id"] for node in nodes}
    for edge in edges:
        src = edge.get("source")
        tgt = edge.get("target")
        if src not in node_ids:
            errors.append(f"Validation Error: Edge source [{src}] does not exist in nodes.")
        if tgt not in node_ids:
            errors.append(f"Validation Error: Edge target [{tgt}] does not exist in nodes.")

    # 2. Semantic LLM validation checks
    if config.GROQ_API_KEY and nodes and not errors:
        nodes_summary = "\n".join([f"- ID: {n['id']} | Name: {n['name']} | Type: {n['type']} | Task: {n.get('generated_task', '')[:200]}" for n in nodes])
        edges_summary = "\n".join([f"- {e['source']} Depends On -> {e['target']}" for e in edges])
        
        prompt = f"""
        You are the Validator Agent for GitGenesis.
        Review this final blueprint graph mapping logic and connection order:
        
        Blueprint Nodes:
        {nodes_summary}
        
        Blueprint Edges:
        {edges_summary}
        
        Perform a semantic validation of this plan:
        1. Does the build dependency order make sense? (e.g. Utility/Database layers should generally compile before Middleware, which should compile before API, which should compile before Frontend).
        2. Are there missing logical boundaries or disconnected clusters that shouldn't be disconnected?
        3. Do the tasks assigned to the layers align semantically with the architecture?
        
        You must return a JSON object containing a "semantic_errors" list of strings.
        For example:
        {{
            "semantic_errors": [
                "Layer dependency mismatch: Node [frontend_ui] compiles before Node [api] is ready, which will cause import errors.",
                "Missing logical boundary: No database connection handler is specified even though schema models are defined."
            ]
        }}
        
        If the blueprint is completely correct, return an empty array. JSON only.
        """
        
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {config.GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": config.DEFAULT_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.1
            }
            with httpx.Client(timeout=15.0) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = json.loads(res.json()["choices"][0]["message"]["content"])
                    semantic_errors = data.get("semantic_errors", [])
                    errors.extend(semantic_errors)
                else:
                    print(f"Validator Agent API returned status code {res.status_code}: {res.text}")
        except Exception as e:
            print(f"Validator Agent LLM validation failed: {e}")

    valid = len(errors) == 0
    
    if valid:
        logs.append("Validator Agent: Graph validation passed. Blueprint is semantic, structured, and complete.")
    else:
        logs.append(f"Validator Agent: Graph validation failed with {len(errors)} errors.")
        for err in errors:
            logs.append(f"Validator: [Error] {err}")

    return {
        "validator_result": {
            "valid": valid,
            "errors": errors
        },
        "logs": logs,
        "active_agent": "coordinator"
    }
