from typing import TypedDict, List, Dict, Any
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

class AgentState(TypedDict):
    knowledge_graph: Dict[str, Any]       # Read-only parsed repository facts
    specialist_outputs: Dict[str, Any]     # Reports gathered from specialists
    blueprint_draft: Dict[str, Any]        # Draft of Executable Engineering Blueprint (nodes/edges)
    critic_feedback: List[str]             # List of feedback loops from Critic
    validator_result: Dict[str, Any]       # Integrity validator report
    active_agent: str                      # Tracking active node
    loop_count: int                        # Counter to prevent infinite debate loops
    logs: List[str]                        # Appended logs for WS monitoring

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
    # The coordinator node decides where to route based on state keys
    workflow.add_conditional_edges(
        "coordinator",
        lambda state: state["active_agent"],
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

    # All parallel specialists route back to coordinator
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
