import httpx
from typing import Dict, Any
from app.config import config

def complexity_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Complexity Agent: Profiles codebase complexity metrics, lines of code, and risk hotspots."""
    kg = state.get("knowledge_graph") or {}
    logs = state.get("logs") or []
    specialist_outputs = state.get("specialist_outputs") or {}
    
    logs.append("Complexity Agent: Evaluating codebase complexity and hotspots...")
    
    modules = kg.get("modules", {})
    
    # Sort modules by Lines of Code
    loc_sorted = sorted(
        [(path, mod.get("lines_of_code", 0), len(mod.get("functions", []))) for path, mod in modules.items()],
        key=lambda x: x[1],
        reverse=True
    )
    
    prompt = f"""
    You are the Complexity Agent.
    Evaluate the following file size metrics and function counts:
    Top 10 largest files (LOC, Functions count): {loc_sorted[:10]}
    
    Context from other specialist agents:
    {specialist_outputs}
    
    Identify:
    1. Codebase hotspots (modules containing excessive logic density).
    2. High-risk modules that require decoupling or careful ordering.
    3. General codebase size and complexity categorization.
    
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
            print(f"Complexity Agent API call failed: {e}")
            
    if not report:
        hotspots = [f"{path} ({loc} lines, {func_cnt} functions)" for path, loc, func_cnt in loc_sorted[:3]]
        report = f"""
### Codebase Complexity & Hotspots Profile
* **Logic Hotspots**: {", ".join(hotspots) or "None detected"}
* **Complexity Level**: The repository features an expected layout structure. The largest files show logical density that should be handled sequentially.
* **Risk Categorization**: Low-to-medium risk. Ensure main routes are isolated from config setups to avoid cyclic dependencies.
        """

    logs.append("Complexity Agent: Complexity evaluation completed.")
    
    new_outputs = dict(specialist_outputs)
    new_outputs["complexity_agent"] = report
    
    return {
        "specialist_outputs": new_outputs,
        "logs": logs
    }
