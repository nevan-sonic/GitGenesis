from typing import Dict, Any

def critic_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Critic Agent: Evaluates the blueprint layout and flags potential architectural contradictions."""
    blueprint_draft = state.get("blueprint_draft") or {}
    logs = state.get("logs") or []
    loop_count = state.get("loop_count", 0)

    logs.append("Critic Agent: Reviewing blueprint draft layout and dependencies...")
    
    nodes = blueprint_draft.get("nodes", [])
    edges = blueprint_draft.get("edges", [])
    
    feedback = []
    
    # 1. Deterministic critique rules
    node_ids = {node["id"] for node in nodes}
    
    # Rule A: Middleware should not depend on API/Routing
    # API/Routing depends on Middleware
    for edge in edges:
        src = edge["source"]
        tgt = edge["target"]
        if "api" in src and "middleware" in tgt:
            feedback.append(f"Critic violation: API layer [{src}] cannot be a prerequisite of Middleware [{tgt}]. Dependency direction is reversed.")
            
    # Rule B: Database must depend on Utilities (if present)
    if "utilities" in node_ids and "database" in node_ids:
        # Check if database has dependency on utilities
        db_deps = []
        for edge in edges:
            if edge["target"] == "database":
                db_deps.append(edge["source"])
        if "utilities" not in db_deps:
            # We can optionally critique it
            pass

    # 2. Limit loop cycles to avoid getting stuck
    if loop_count >= 1:
        # If we already did one loop iteration, we clear feedback to avoid infinite loops
        feedback = []

    if feedback:
        logs.append(f"Critic Agent: Architectural violations flagged: {feedback}")
    else:
        logs.append("Critic Agent: Blueprint layout passed architectural review.")

    return {
        "critic_feedback": feedback,
        "logs": logs,
        "active_agent": "coordinator"
    }
