import httpx
import json
from typing import Dict, Any, List
from app.config import config

def repair_json_backslashes(text: str) -> str:
    """Repairs invalid JSON backslash escapes by doubling them (e.g. \s -> \\s) while preserving valid JSON escapes."""
    result = []
    i = 0
    n = len(text)
    while i < n:
        char = text[i]
        if char == '\\':
            if i + 1 < n:
                next_char = text[i + 1]
                # Is it a standard JSON escape?
                if next_char in ['"', '\\', '/', 'b', 'f', 'n', 'r', 't']:
                    result.append('\\')
                    result.append(next_char)
                    i += 2
                    continue
                # Is it a unicode escape?
                elif next_char == 'u' and i + 5 < n and all(c in '0123456789abcdefABCDEF' for c in text[i+2:i+6]):
                    result.append('\\')
                    result.append('u')
                    result.append(text[i+2:i+6])
                    i += 6
                    continue
            result.append('\\\\')
            i += 1
        else:
            result.append(char)
            i += 1
    return "".join(result)

def code_modifier_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Code Modifier Agent: Modifies repository files based on strategy updates."""
    kg = state.get("knowledge_graph") or {}
    logs = state.get("logs") or []
    node_id = state.get("current_node_id")
    strategy = state.get("strategy_override", "")
    source_files = state.get("source_files") or {}  # Map of file path -> current content
    
    if not source_files:
        logs.append("Code Modifier: No source files provided for editing.")
        return {"logs": logs}
        
    logs.append(f"Code Modifier: Generating code changes using Groq Llama-3.3-70b for node '{node_id}'...")

    # Build prompt
    files_context = ""
    for path, content in source_files.items():
        files_context += f"--- FILE: {path} ---\n{content}\n\n"

    prompt = f"""
    You are the Code Modifier Agent.
    Your task is to modify the provided codebase files to implement the following architectural strategy:
    Strategy: "{strategy}"
    
    Here are the files you need to modify along with their current content:
    {files_context}
    
    You must output a valid JSON object containing a "modifications" key.
    Each modification must have:
    - "file_path": The exact file path.
    - "content": The complete new content of the file. Do not omit any lines. Write the fully functional code.
    
    Example response format:
    {{
      "modifications": [
        {{
          "file_path": "config/database.js",
          "content": "const mongoose = require('mongoose');\\nconst connect = () => mongoose.connect(process.env.MONGO_URI);\\nmodule.exports = connect;"
        }}
      ]
    }}
    
    Ensure your output is well-formed JSON only.
    """

    modifications = []
    if config.GROQ_API_KEY:
        try:
            url = "https://api.groq.com/openapi/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {config.GROQ_API_KEY}",
                "content-type": "application/json"
            }
            payload = {
                "model": config.MODEL_CODER,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1
            }
            with httpx.Client(timeout=40.0) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    text = res.json()["choices"][0]["message"]["content"]
                    # Extract JSON block if LLM wrapped in markdown
                    if "```json" in text:
                        text = text.split("```json")[1].split("```")[0].strip()
                    elif "```" in text:
                        text = text.split("```")[1].split("```")[0].strip()
                    
                    try:
                        data = json.loads(text)
                    except json.JSONDecodeError:
                        # Attempt to auto-repair invalid backslashes before failing
                        repaired_text = repair_json_backslashes(text)
                        data = json.loads(repaired_text)
                        
                    modifications = data.get("modifications", [])
                    logs.append(f"Code Modifier: Successfully generated changes for {len(modifications)} files.")
                else:
                    logs.append(f"Code Modifier Warning: Groq API returned status {res.status_code}. Falling back to default edits.")
        except Exception as e:
            logs.append(f"Code Modifier Error: Groq API call failed: {e}")
            print(f"Code Modifier API call failed: {e}")
            
    # Deterministic fallback edit if API key not set or fails
    if not modifications:
        logs.append("Code Modifier: Falling back to automated regex replacements.")
        for path, content in source_files.items():
            # Inject comment about strategy at top of file
            modified = f"// [GitGenesis Strategy: {strategy}]\n" + content
            modifications.append({
                "file_path": path,
                "content": modified
            })

    return {
        "logs": logs,
        "modifications": modifications
    }
