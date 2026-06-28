import httpx
from typing import Dict, Any
from app.config import config

def dependency_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Dependency Agent: Resolves sequence dependencies and build order constraints."""
    kg = state.get("knowledge_graph") or {}
    logs = state.get("logs") or []
    specialist_outputs = state.get("specialist_outputs") or {}
    
    logs.append("Dependency Agent: Resolving execution and sequence constraints...")
    
    modules = kg.get("modules", {})
    edges = kg.get("edges", [])
    
    # Calculate top imported files
    import_counts = {}
    for edge in edges:
        if edge.get("relation") == "IMPORTS":
            target = edge["target"].replace("module:", "")
            import_counts[target] = import_counts.get(target, 0) + 1
            
    sorted_imports = sorted(import_counts.items(), key=lambda x: x[1], reverse=True)
    
    prompt = f"""
    You are the Dependency Agent.
    Review this summary of import relationships and dependencies in the repository:
    Total dependency links: {len([e for e in edges if e.get("relation") == "IMPORTS"])}
    Heavily imported files (shared dependencies): {sorted_imports[:10]}
    
    Determine:
    1. The core foundation components that have no dependencies (e.g. database schema configs, helpers).
    2. The logical sequence/pipeline order to build these components (e.g. Database -> Models -> Controllers -> UI).
    3. Prerequisite pathways and circular dependencies.
    
    Write a concise summary report.
    """
    
    report = ""
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
            print(f"Dependency Agent API call failed: {e}")
            
    if not report:
        top_deps = [f"{path} (imported by {count} files)" for path, count in sorted_imports[:3]]
        report = f"""
### Dependency Pathway Report
* **Top Foundational Modules**: {", ".join(top_deps) or "None detected"}
* **Build Sequence**: Foundation configs and database schemas must be loaded prior to importing route handlers or initializing web server applications.
* **Prerequisites Checklist**: Ensure utility wrappers are instantiated before layers containing business logic are invoked.
        """

    logs.append("Dependency Agent: Dependency sequence resolved.")
    
    new_outputs = dict(specialist_outputs)
    new_outputs["dependency_agent"] = report
    
    return {
        "specialist_outputs": new_outputs,
        "logs": logs
    }
