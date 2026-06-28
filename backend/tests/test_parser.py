import os
import tempfile
import pytest
from app.services.static_analysis_engine import StaticAnalysisEngine
from app.services.knowledge_graph_builder import KnowledgeGraphBuilder

def test_static_analysis_and_kg_builder():
    analyzer = StaticAnalysisEngine()
    builder = KnowledgeGraphBuilder()
    
    # Create a temp directory with mock codebase files
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create package.json
        with open(os.path.join(tmpdir, "package.json"), "w") as f:
            f.write('{"dependencies": {"react": "^18.2.0", "next": "14.0.0"}}')
            
        # Create a mock typescript utility module
        with open(os.path.join(tmpdir, "utils.ts"), "w") as f:
            f.write("export function formatText(text: string) { return text.trim(); }")
            
        # Create a mock API route
        with open(os.path.join(tmpdir, "api.ts"), "w") as f:
            f.write("import { formatText } from './utils';\nexport function handler() { return formatText('hello'); }")

        # Run static analysis
        facts = analyzer.analyze_repository(tmpdir)
        
        # Verify deterministic output details
        assert "package.json" in facts["config_files"]
        assert "utils.ts" in facts["parsed_files"]
        assert "api.ts" in facts["parsed_files"]
        assert "Next.js" in facts["frameworks"]
        
        # Build Knowledge Graph
        kg = builder.build_knowledge_graph(facts)
        
        # Verify node counts
        assert len(kg["nodes"]) >= 3  # config, utilities module, routing/api module
        
        # Verify import link resolution
        api_node = next((n for n in kg["nodes"] if n["id"] == "module:api.ts"), None)
        assert api_node is not None
        
        edges = kg["edges"]
        import_edge = next((e for e in edges if e["source"] == "module:api.ts" and e["target"] == "module:utils.ts"), None)
        assert import_edge is not None
        assert import_edge["relation"] == "IMPORTS"
