from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph import StateGraph, END
from app.agents.coordinator import coordinator_node
from app.agents.specialists.analyst import analyst_node
from app.agents.specialists.architect import architect_node
from app.agents.specialists.dependency import dependency_node
from app.agents.specialists.complexity import complexity_node
from app.agents.specialists.documentation import documentation_node
from app.agents.planner import planner_node
from app.agents.critic import critic_node
from app.agents.validator import validator_node

# Reducer to merge specialist report dictionaries from concurrent threads
def merge_specialist_outputs(left: dict, right: dict) -> dict:
    return {**(left or {}), **(right or {})}

# Reducer to merge logs from concurrent threads distinctly
def append_logs(left: list, right: list) -> list:
    new_logs = list(left or [])
    for item in (right or []):
        if item not in new_logs:
            new_logs.append(item)
    return new_logs

class AgentState(TypedDict):
    knowledge_graph: Dict[str, Any]       # Read-only parsed repository facts
    specialist_outputs: Annotated[Dict[str, Any], merge_specialist_outputs]
    blueprint_draft: Dict[str, Any]        # Draft of Executable Engineering Blueprint (nodes/edges)
    critic_feedback: List[str]             # List of feedback loops from Critic
    validator_result: Dict[str, Any]       # Integrity validator report
    active_agent: str                      # Tracking active node
    loop_count: int                        # Counter to prevent infinite debate loops
    logs: Annotated[List[str], append_logs] # Appended logs for WS monitoring

def route_next_agent(state: AgentState):
    active = state.get("active_agent")
    if active == "run_specialists":
        # Returns list to execute multiple nodes concurrently in LangGraph
        return ["repository_analyst", "architecture_agent", "dependency_agent", "complexity_agent", "documentation_agent"]
    return active

def build_workflow() -> StateGraph:
    """Configures the LangGraph StateGraph mapping Coordinator routing and specialist nodes."""
    workflow = StateGraph(AgentState)

    # 1. Define nodes
    workflow.add_node("coordinator", coordinator_node)
    workflow.add_node("repository_analyst", analyst_node)
    workflow.add_node("architecture_agent", architect_node)
    workflow.add_node("dependency_agent", dependency_node)
    workflow.add_node("complexity_agent", complexity_node)
    workflow.add_node("documentation_agent", documentation_node)
    workflow.add_node("blueprint_planner", planner_node)
    workflow.add_node("critic_agent", critic_node)
    workflow.add_node("validator_agent", validator_node)

    # 2. Set Entry point
    workflow.set_entry_point("coordinator")

    # 3. Define routing rules (Conditional Edges)
    workflow.add_conditional_edges(
        "coordinator",
        route_next_agent,
        {
            "repository_analyst": "repository_analyst",
            "architecture_agent": "architecture_agent",
            "dependency_agent": "dependency_agent",
            "complexity_agent": "complexity_agent",
            "documentation_agent": "documentation_agent",
            "blueprint_planner": "blueprint_planner",
            "critic_agent": "critic_agent",
            "validator_agent": "validator_agent",
            "end": END
        }
    )

    # All parallel specialists route back to coordinator (join step)
    workflow.add_edge("repository_analyst", "coordinator")
    workflow.add_edge("architecture_agent", "coordinator")
    workflow.add_edge("dependency_agent", "coordinator")
    workflow.add_edge("complexity_agent", "coordinator")
    workflow.add_edge("documentation_agent", "coordinator")
    
    # Planner, Critic, and Validator route back to coordinator to manage routing state
    workflow.add_edge("blueprint_planner", "coordinator")
    workflow.add_edge("critic_agent", "coordinator")
    workflow.add_edge("validator_agent", "coordinator")

    return workflow.compile()
