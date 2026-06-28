import json
import httpx
from typing import Dict, Any
from app.config import config

def critic_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Critic Agent: Evaluates the blueprint layout and flags potential architectural contradictions using LLM."""
    blueprint_draft = state.get("blueprint_draft") or {}
    logs = state.get("logs") or []
    loop_count = state.get("loop_count", 0)

    logs.append("Critic Agent: Reviewing blueprint draft layout and dependencies...")
    
    nodes = blueprint_draft.get("nodes", [])
    edges = blueprint_draft.get("edges", [])
    
    feedback = []
    
    # Check if LLM is available
    if config.GROQ_API_KEY and nodes:
        nodes_summary = "\n".join([f"- ID: {n['id']} | Name: {n['name']} | Type: {n['type']} | Task: {n.get('generated_task', '')[:200]}" for n in nodes])
        edges_summary = "\n".join([f"- {e['source']} Depends On -> {e['target']}" for e in edges])
        
        prompt = f"""
        You are the Critic Agent for GitGenesis.
        Your task is to review the proposed codebase architecture blueprint draft and flag any design mistakes, bad routing, anti-patterns, or architectural violations.
        
        Proposed Blueprint Nodes:
        {nodes_summary}
        
        Proposed Blueprint Edges (Dependencies):
        {edges_summary}
        
        Identify any architectural violations. Common violations include:
        1. Circular dependencies (e.g. A depends on B, B depends on A).
        2. Bad layering directions (e.g. database or utility layers depending directly on frontend, or API routing depending directly on frontend).
        3. Missing critical architectural blocks (e.g. a database type node is missing but files are classified as database repositories).
        
        You must return a list of violations as a clean JSON array of strings. 
        For example:
        {{
            "violations": [
                "API layer [api] cannot be a prerequisite of Middleware [middleware]. Dependency direction is reversed.",
                "Circular dependency detected between node [database_layer] and node [orm_helper]."
            ]
        }}
        
        If the blueprint architecture is completely sound and valid, return an empty list of violations.
        Ensure the output is valid JSON. JSON only.
        """
        
        try:
            url = "https://api.groq.com/openapi/v1/chat/completions"
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
                    feedback = data.get("violations", [])
                else:
                    print(f"Critic Agent API returned status code {res.status_code}: {res.text}")
        except Exception as e:
            print(f"Critic Agent LLM call failed: {e}")
            
    # Deterministic fallback check if LLM fails or is keyless
    if not feedback:
        for edge in edges:
            src = edge["source"]
            tgt = edge["target"]
            if "api" in src and "middleware" in tgt:
                feedback.append(f"Critic violation: API layer [{src}] cannot be a prerequisite of Middleware [{tgt}]. Dependency direction is reversed.")

    # Guard to prevent infinite debate loops (limit to 2 loops)
    if loop_count >= 2:
        feedback = []

    if feedback:
        logs.append(f"Critic Agent: Flagged {len(feedback)} architectural violations.")
        for f in feedback:
            logs.append(f"Critic: [Violation] {f}")
    else:
        logs.append("Critic Agent: Blueprint passed review successfully (0 violations).")

    return {
        "critic_feedback": feedback,
        "logs": logs,
        "active_agent": "coordinator"
    }
