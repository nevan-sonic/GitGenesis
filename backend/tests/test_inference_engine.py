import pytest
from app.services.inference_engine import InferenceEngine
from typing import List, Dict, Any

class MockGraphRepository:
    def create_blueprint(self, blueprint_id, repository_id, name): pass
    def create_branch(self, branch_id, blueprint_id, name, active): pass
    def add_node(self, **kwargs): pass
    def add_edge(self, **kwargs): pass
    def get_active_branch(self, blueprint_id):
        return {"id": "mock_branch_id"}

class MockEmbeddingService:
    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        return [[0.1] * 768 for _ in texts]

def test_inference_engine_node_merging():
    repo = MockGraphRepository()
    emb = MockEmbeddingService()
    engine = InferenceEngine(repo, emb)

    # 1. Test Node Merging
    nodes = [
        {"id": "auth", "name": "Authentication", "type": "middleware", "confidence_score": 90, "supporting_evidence": ["auth.ts"]},
        {"id": "auth", "name": "Authentication", "type": "middleware", "confidence_score": 80, "supporting_evidence": ["package.json"]}
    ]
    
    merged = engine._merge_nodes(nodes)
    
    assert "auth" in merged
    assert merged["auth"]["confidence_score"] == 85  # Average score (90+80)/2
    assert "auth.ts" in merged["auth"]["supporting_evidence"]
    assert "package.json" in merged["auth"]["supporting_evidence"]

def test_inference_engine_cycle_prevention():
    repo = MockGraphRepository()
    emb = MockEmbeddingService()
    engine = InferenceEngine(repo, emb)

    # 2. Test Cycle Elimination (A -> B -> A)
    nodes = {
        "A": {"name": "Node A"},
        "B": {"name": "Node B"}
    }
    edges = [
        {"source": "A", "target": "B"},
        {"source": "B", "target": "A"}  # Cycle edge
    ]

    cleaned = engine._remove_cycles(nodes, edges)
    
    # Assert only one edge is kept, eliminating the cyclic back-edge
    assert len(cleaned) == 1
    assert cleaned[0]["source"] == "A"
    assert cleaned[0]["target"] == "B"
