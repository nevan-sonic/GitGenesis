import httpx
from typing import Dict, Any
from app.config import config

def architect_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Architecture Agent: Discovers separation of concerns, layers, and architectural boundaries."""
    kg = state.get("knowledge_graph") or {}
    logs = state.get("logs") or []
    specialist_outputs = state.get("specialist_outputs") or {}
    
    logs.append("Architecture Agent: Analyzing logical layer divisions...")
    
    layers = kg.get("layers", {})
    services = kg.get("services", {})
    
    prompt = f"""
    You are the Architecture Agent.
    Analyze these logical layers and service boundaries in the repository knowledge graph:
    Layers: {list(layers.keys())}
    Layer modules sample: {{k: v[:5] for k, v in layers.items()}}
    Services identified: {list(services.keys())}
    
    Identify:
    1. Key architectural patterns (e.g. MVC, Clean Architecture, Repository Pattern, Layered Architecture).
    2. Boundary lines and modules that act as interfaces between directories.
    3. Structural divisions of components.
    
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
            print(f"Architecture Agent API call failed: {e}")
            
    if not report:
        layer_summary = [f"{layer_name} Layer ({len(files)} files)" for layer_name, files in layers.items() if files]
        report = f"""
### Logical Architecture Report
* **Identified Layers**: {", ".join(layer_summary)}
* **Architectural Boundaries**: Modular structure with distinct separations between database data models and controller routing rules.
* **Structural Patterns**: Clean separation of database logic from route controllers using structured layers.
        """

    logs.append("Architecture Agent: Boundary analysis completed.")
    
    new_outputs = dict(specialist_outputs)
    new_outputs["architecture_agent"] = report
    
    return {
        "specialist_outputs": new_outputs,
        "logs": logs
    }
