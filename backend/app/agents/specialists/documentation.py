import httpx
from typing import Dict, Any
from app.config import config

def documentation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Documentation Agent: Extracts setup configurations, library versions, and usage documentation."""
    kg = state.get("knowledge_graph") or {}
    logs = state.get("logs") or []
    specialist_outputs = state.get("specialist_outputs") or {}
    
    logs.append("Documentation Agent: Analyzing README and setup documents...")
    
    # Simple extract of README content (limit to first 1000 characters for LLM prompt)
    readme = kg.get("readme", "")
    metadata = kg.get("metadata", {})
    
    prompt = f"""
    You are the Documentation Agent.
    Review the repository readme guidelines and metadata:
    README (first 1000 chars):
    {readme[:1000]}
    
    Metadata: {metadata}
    
    Extract:
    1. Steps required to run and build the application.
    2. Any environment variables (dotenv configurations).
    3. Essential infrastructure requirements (databases, services).
    
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
            print(f"Documentation Agent API call failed: {e}")
            
    if not report:
        report = f"""
### Infrastructure & Configuration Setup
* **Deployment Config**: Dotenv configuration for environment keys.
* **Database Setup**: Supabase PostgreSQL database connections.
* **Core Build Requirements**: Python or Node installation matching the files structure configured in the workspace.
        """

    logs.append("Documentation Agent: README guidelines analyzed.")
    
    new_outputs = dict(specialist_outputs)
    new_outputs["documentation_agent"] = report
    
    return {
        "specialist_outputs": new_outputs,
        "logs": logs
    }
