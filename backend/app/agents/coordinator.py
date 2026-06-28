from typing import Dict, Any

def coordinator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Orchestrates multi-agent execution, schedules specialists, manages loop counts, and routes control."""
    specialist_outputs = state.get("specialist_outputs") or {}
    critic_feedback = state.get("critic_feedback") or []
    validator_result = state.get("validator_result") or {}
    loop_count = state.get("loop_count", 0)
    blueprint_draft = state.get("blueprint_draft") or {}
    logs = state.get("logs") or []

    # Initialize log tracking
    updated_logs = list(logs)

    # 1. Schedule specialists concurrently (Parallel fanning out in LangGraph)
    specialist_keys = ["repository_analyst", "architecture_agent", "dependency_agent", "complexity_agent", "documentation_agent"]
    
    missing_specialists = [k for k in specialist_keys if k not in specialist_outputs]
    if missing_specialists:
        updated_logs.append("Coordinator: Dispatching parallel specialist agent cluster (Repository Analyst, Architecture, Dependency, Complexity, Documentation)...")
        return {
            "active_agent": "run_specialists",
            "logs": updated_logs
        }

    # 2. If specialists completed but no blueprint draft exists, schedule Planner
    if not blueprint_draft:
        updated_logs.append("Coordinator: Specialist reports gathered. Scheduling [blueprint_planner] to compile Executable Engineering Blueprint draft...")
        return {
            "active_agent": "blueprint_planner",
            "logs": updated_logs
        }

    # 3. If draft exists, but critic hasn't reviewed yet, schedule Critic
    # We trace if a critic has run by checking if loop_count is incremented or critic feedback exists.
    # To keep state clean, if active_agent was blueprint_planner, we run critic next.
    if state.get("active_agent") == "blueprint_planner":
        updated_logs.append("Coordinator: Blueprint draft generated. Scheduling [critic_agent] to review and challenge architecture choices...")
        return {
            "active_agent": "critic_agent",
            "logs": updated_logs
        }

    # 4. Handle Critic feedback loops
    if state.get("active_agent") == "critic_agent":
        if critic_feedback and loop_count < 2:
            updated_logs.append(f"Coordinator: Critic requested revisions (Iteration {loop_count + 1}). Re-routing to [blueprint_planner]...")
            return {
                "active_agent": "blueprint_planner",
                "loop_count": loop_count + 1,
                "logs": updated_logs
            }
        else:
            updated_logs.append("Coordinator: Critic checks complete. Scheduling [validator_agent] for final consistency check...")
            return {
                "active_agent": "validator_agent",
                "logs": updated_logs
            }

    # 5. Check Validator results
    if state.get("active_agent") == "validator_agent":
        is_valid = validator_result.get("valid", True)
        if not is_valid and loop_count < 3:
            updated_logs.append("Coordinator: Validator detected inconsistencies. Re-routing back to [blueprint_planner]...")
            return {
                "active_agent": "blueprint_planner",
                "loop_count": loop_count + 1,
                "logs": updated_logs
            }
            
        updated_logs.append("Coordinator: Executable Engineering Blueprint successfully validated. Ending multi-agent workspace run.")
        return {
            "active_agent": "end",
            "logs": updated_logs
        }

    # Fallback safety exit
    return {
        "active_agent": "end",
        "logs": updated_logs
    }
