import uuid
from typing import Dict, List, Any, Optional
from app.repositories.graph_repository import GraphRepository
from app.services.embedding_service import EmbeddingService

class InferenceEngine:
    def __init__(self, repo: GraphRepository, embedding_service: EmbeddingService):
        self.repo = repo
        self.embedding_service = embedding_service

    def persist_executable_blueprint(self, blueprint_id: str, repository_id: int, name: str, 
                                     agent_nodes: List[Dict[str, Any]], agent_edges: List[Dict[str, Any]],
                                     user_id: Optional[str] = None) -> str:
        """Processes, merges, validates, embeds, and saves an Executable Engineering Blueprint."""
        print(f"Inference Engine: Processing blueprint {name} ({blueprint_id})...")
        
        # 1. Resolve conflicts and merge duplicates in agent node outputs
        merged_nodes = self._merge_nodes(agent_nodes)
        
        # 2. Validate edge constraints (dangling references, cyclic dependencies)
        valid_edges = self._validate_and_cleanup_edges(merged_nodes, agent_edges)
        
        # 3. Create the base blueprint and default master branch records
        self.repo.create_blueprint(blueprint_id, repository_id, name, user_id)
        
        # We always initialize with a default "master" branch
        branch_id = str(uuid.uuid4())
        self.repo.create_branch(branch_id, blueprint_id, name="master", active=True)
        
        # 4. Generate embeddings and persist nodes in a batch
        node_texts = []
        node_ids_ordered = []
        for nid, node in merged_nodes.items():
            # Construct text representation for embedding similarity searches
            searchable_text = f"Node: {node['name']}\nType: {node['type']}\nSummary: {node['architectural_reasoning_summary']}\nTask: {node['generated_task']}"
            node_texts.append(searchable_text)
            node_ids_ordered.append(nid)

        # Batch embed all nodes
        embeddings = self.embedding_service.get_embeddings_batch(node_texts)
        
        # Save nodes
        for idx, nid in enumerate(node_ids_ordered):
            node = merged_nodes[nid]
            embedding = embeddings[idx]
            
            self.repo.add_node(
                node_id=nid,
                blueprint_id=blueprint_id,
                branch_id=branch_id,
                name=node["name"],
                node_type=node["type"],
                confidence_score=node["confidence_score"],
                supporting_evidence=node["supporting_evidence"],
                architectural_reasoning_summary=node["architectural_reasoning_summary"],
                source_files=node["source_files"],
                dependency_references=node["dependency_references"],
                related_modules=node["related_modules"],
                generated_task=node["generated_task"],
                embedding=embedding,
                confidence_explanation=node.get("confidence_explanation", "")
            )

        # 5. Persist edges
        for idx, edge in enumerate(valid_edges):
            edge_id = f"edge_{idx}"
            self.repo.add_edge(
                edge_id=edge_id,
                blueprint_id=blueprint_id,
                branch_id=branch_id,
                source_id=edge["source"],
                target_id=edge["target"],
                relation_type=edge.get("relation_type", "DEPENDS_ON")
            )

        print(f"Inference Engine: Successfully persisted Executable Engineering Blueprint {blueprint_id}.")
        return branch_id

    def _merge_nodes(self, nodes: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Combines nodes with identical IDs, resolving conflict parameters (confidence, evidence)."""
        merged: Dict[str, Dict[str, Any]] = {}
        
        for node in nodes:
            nid = node["id"]
            
            # Helper to normalize confidence score to integer percentage
            raw_conf = node.get("confidence_score", 90)
            try:
                # Handle cases where score is string, float in [0, 1] or outside
                conf_val = float(raw_conf)
                if conf_val <= 1.0:
                    conf_val = conf_val * 100
                conf = int(conf_val)
            except (TypeError, ValueError):
                conf = 90
            conf = max(0, min(100, conf))

            if nid not in merged:
                merged[nid] = {
                    "name": node.get("name", nid),
                    "type": node.get("type", "layer"),
                    "confidence_score": conf,
                    "confidence_explanation": node.get("confidence_explanation", ""),
                    "supporting_evidence": list(set(node.get("supporting_evidence", []))),
                    "architectural_reasoning_summary": node.get("architectural_reasoning_summary", ""),
                    "source_files": list(set(node.get("source_files", []))),
                    "dependency_references": list(set(node.get("dependency_references", []))),
                    "related_modules": list(set(node.get("related_modules", []))),
                    "generated_task": node.get("generated_task", "")
                }
            else:
                # Merge duplicate recommendations: average confidence, combine evidence/files
                existing = merged[nid]
                existing["confidence_score"] = int((existing["confidence_score"] + conf) / 2)
                existing["supporting_evidence"] = list(set(existing["supporting_evidence"] + node.get("supporting_evidence", [])))
                existing["source_files"] = list(set(existing["source_files"] + node.get("source_files", [])))
                existing["dependency_references"] = list(set(existing["dependency_references"] + node.get("dependency_references", [])))
                existing["related_modules"] = list(set(existing["related_modules"] + node.get("related_modules", [])))
                
                # Append summaries/explanations if they differ
                if node.get("architectural_reasoning_summary") and node["architectural_reasoning_summary"] not in existing["architectural_reasoning_summary"]:
                    existing["architectural_reasoning_summary"] += "\n" + node["architectural_reasoning_summary"]
                if node.get("confidence_explanation") and node["confidence_explanation"] not in existing.get("confidence_explanation", ""):
                    if existing.get("confidence_explanation"):
                        existing["confidence_explanation"] += " " + node["confidence_explanation"]
                    else:
                        existing["confidence_explanation"] = node["confidence_explanation"]
                    
        return merged

    def _validate_and_cleanup_edges(self, nodes: Dict[str, Any], edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Cleans up edge lists, removing dangling nodes and breaking graph dependency cycles."""
        valid_edges = []
        for edge in edges:
            src = edge.get("source")
            tgt = edge.get("target")
            
            # Check for dangling nodes
            if src in nodes and tgt in nodes:
                valid_edges.append(edge)
                
        # Cycle detection and removal (DFS)
        return self._remove_cycles(nodes, valid_edges)

    def _remove_cycles(self, nodes: Dict[str, Any], edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Quick DFS cycle detection
        adj = {nid: [] for nid in nodes}
        for edge in edges:
            adj[edge["source"]].append(edge)

        visited = {}  # 0 = unvisited, 1 = visiting, 2 = visited
        cleaned_edges = []
        
        def dfs(node_id):
            visited[node_id] = 1  # visiting
            for edge in adj[node_id]:
                neighbor = edge["target"]
                if visited.get(neighbor, 0) == 0:
                    cleaned_edges.append(edge)
                    if not dfs(neighbor):
                        return False
                elif visited.get(neighbor, 0) == 1:
                    # Found a cycle! Drop this back-edge
                    print(f"Inference Engine: Cycle detected from {node_id} to {neighbor}. Breaking cycle.")
                    continue
                else:
                    cleaned_edges.append(edge)
            visited[node_id] = 2  # visited
            return True

        for nid in nodes:
            if visited.get(nid, 0) == 0:
                dfs(nid)
                
        return cleaned_edges
