import json
from typing import List, Dict, Any

class Exporter:
    @staticmethod
    def export_blueprint(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], export_format: str) -> str:
        """Packs the blueprint nodes and edges into the requested export format."""
        fmt = export_format.lower().strip()
        
        if fmt == "json":
            return Exporter._export_json(nodes, edges)
        elif fmt == "markdown":
            return Exporter._export_markdown(nodes, edges)
        elif fmt == "dag":
            return Exporter._export_dag(nodes, edges)
        elif fmt == "codex":
            return Exporter._export_codex(nodes)
        elif fmt == "cursor":
            return Exporter._export_cursor(nodes)
        elif fmt == "workflow":
            return Exporter._export_workflow(nodes, edges)
        else:
            raise ValueError(f"Unknown export format: {export_format}")

    @staticmethod
    def _export_json(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> str:
        return json.dumps({
            "artifact_type": "Executable Engineering Blueprint",
            "nodes": nodes,
            "edges": edges
        }, indent=2)

    @staticmethod
    def _export_markdown(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> str:
        md = []
        md.append("# Executable Engineering Blueprint\n")
        md.append("This document contains the AI-executable task roadmap for rebuilding this repository.\n")
        
        md.append("## Build Nodes Checklist")
        for node in nodes:
            md.append(f"### [ ] {node['name']} (Confidence: {node.get('confidence_score', 0)}%)")
            md.append(f"**Type**: `{node.get('type')}`")
            md.append(f"**Evidence**: `{', '.join(node.get('supporting_evidence', []))}`\n")
            md.append(f"**Reasoning**: {node.get('architectural_reasoning_summary')}\n")
            md.append("#### Generated Task Instructions:")
            md.append(f"```\n{node.get('generated_task')}\n```\n")
            md.append("---")
            
        md.append("## Dependency Connections")
        for edge in edges:
            md.append(f"- `{edge['source_id']}` &rarr; `{edge['target_id']}` (`{edge.get('relation_type', 'DEPENDS_ON')}`)")
            
        return "\n".join(md)

    @staticmethod
    def _export_dag(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> str:
        # Export as a simple DOT representation for graphviz or layout engines
        dot = ["digraph G {"]
        dot.append("  rankdir=LR;")
        dot.append("  node [shape=box, style=filled, color=lightblue];")
        
        for node in nodes:
            dot.append(f'  "{node["id"]}" [label="{node["name"]}\\n({node.get("type")})"];')
            
        for edge in edges:
            dot.append(f'  "{edge["source_id"]}" -> "{edge["target_id"]}" [label="{edge.get("relation_type", "")}"];')
            
        dot.append("}")
        return "\n".join(dot)


    @staticmethod
    def _export_codex(nodes: List[Dict[str, Any]]) -> str:
        # Task instructions optimized for Codex
        codex = []
        codex.append("# Codex Implementation Instructions")
        for node in nodes:
            codex.append(f"### Implement {node['name']}")
            codex.append(f"File References: {node.get('source_files', [])}")
            codex.append(f"Context: {node.get('architectural_reasoning_summary')}")
            codex.append(f"Instructions:\n{node.get('generated_task')}")
            codex.append("\n===\n")
        return "\n".join(codex)

    @staticmethod
    def _export_cursor(nodes: List[Dict[str, Any]]) -> str:
        # Export as a structured .cursorrules file
        rules = {
            "version": "1.0",
            "title": "Genesis Executable Engineering Blueprint",
            "tasks": []
        }
        for node in nodes:
            rules["tasks"].append({
                "node_id": node["id"],
                "name": node["name"],
                "description": node.get("architectural_reasoning_summary", ""),
                "rules": node.get("generated_task", "").splitlines()
            })
        return json.dumps(rules, indent=2)

    @staticmethod
    def _export_workflow(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> str:
        # Export a structured workflow manifest DAG
        workflow = {
            "name": "genesis-blueprint-workflow",
            "stages": []
        }
        for node in nodes:
            # Find dependencies
            depends_on = []
            for edge in edges:
                if edge["target_id"] == node["id"]:
                    depends_on.append(edge["source_id"])
                    
            workflow["stages"].append({
                "id": node["id"],
                "name": node["name"],
                "type": node.get("type"),
                "depends_on": depends_on,
                "task": {
                    "instructions": node.get("generated_task"),
                    "files": node.get("source_files")
                }
            })
        return json.dumps(workflow, indent=2)
