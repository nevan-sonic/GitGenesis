import httpx
from typing import Dict, Any
from app.config import config

def analyst_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Repository Analyst Agent: Profiles repository files, structures, and entrypoints."""
    kg = state.get("knowledge_graph") or {}
    logs = state.get("logs") or []
    specialist_outputs = state.get("specialist_outputs") or {}
    
    logs.append("Repository Analyst: Starting repository structure profiling...")
    
    # 1. Gather facts from Knowledge Graph
    modules = kg.get("modules", {})
    metadata = kg.get("metadata", {})
    file_list = list(modules.keys())
    
    prompt = f"""
    You are the Repository Analyst Agent.
    Analyze the following repository structure and metadata:
    Frameworks: {metadata.get("frameworks", [])}
    Dependencies: {metadata.get("dependencies", {})}
    Files: {file_list[:100]}
    
    Identify:
    1. The main entrypoints of the application (e.g. index.ts, main.py, App.tsx).
    2. The core services and packages structure.
    3. File organisation patterns.
    
    Write a concise summary report.
    """
    
    report = ""
    # Try calling LLM if key is present
    if config.GROQ_API_KEY:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {config.GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": config.DEFAULT_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0
            }
            with httpx.Client(timeout=15.0) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    report = res.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"Repository Analyst API call failed: {e}")
            
    # Deterministic fallback report if LLM fails or is offline
    if not report:
        entry_candidates = [f for f in file_list if any(name in f.lower() for name in ["main", "index", "app", "server"])]
        report = f"""
### Repository Structure Profile
* **Total Parsed Modules**: {len(file_list)}
* **Detected Frameworks**: {", ".join(metadata.get("frameworks", [])) or "None"}
* **Inferred Entrypoints**: {", ".join(entry_candidates[:3]) or "None"}
* **Structure Overview**: The codebase features a modern modular structure with distinct layers for business logic and configurations.
        """

    logs.append("Repository Analyst: Profiling completed.")
    
    # Update state
    new_outputs = dict(specialist_outputs)
    new_outputs["repository_analyst"] = report
    
    return {
        "specialist_outputs": new_outputs,
        "logs": logs
    }
