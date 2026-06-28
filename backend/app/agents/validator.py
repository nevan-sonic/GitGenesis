from typing import Dict, Any

def validator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Validator Agent: Performs final semantic checks and graph validation."""
    blueprint_draft = state.get("blueprint_draft") or {}
    logs = state.get("logs") or []
    
    logs.append("Validator Agent: Running final semantic validation checks...")
    
    nodes = blueprint_draft.get("nodes", [])
    edges = blueprint_draft.get("edges", [])
    
    errors = []
    
    # Check 1: Ensure we have nodes in the blueprint
    if not nodes:
        errors.append("Validation Error: Executable Engineering Blueprint must contain at least one node.")
        
    # Check 2: Ensure all nodes have tasks
    for node in nodes:
        if not node.get("generated_task") or not node["generated_task"].strip():
            errors.append(f"Validation Error: Node [{node['id']}] does not contain an AI task description.")

    # Check 3: Check for dangling edges
    node_ids = {node["id"] for node in nodes}
    for edge in edges:
        src = edge.get("source")
        tgt = edge.get("target")
        if src not in node_ids:
            errors.append(f"Validation Error: Edge source [{src}] does not exist in nodes.")
        if tgt not in node_ids:
            errors.append(f"Validation Error: Edge target [{tgt}] does not exist in nodes.")

    valid = len(errors) == 0
    
    if valid:
        logs.append("Validator Agent: Graph validation passed. Blueprint is semantic and complete.")
    else:
        logs.append(f"Validator Agent: Graph validation failed: {errors}")

    return {
        "validator_result": {
            "valid": valid,
            "errors": errors
        },
        "logs": logs,
        "active_agent": "coordinator"
    }
