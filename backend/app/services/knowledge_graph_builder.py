import os
import re
from typing import Dict, List, Any

class KnowledgeGraphBuilder:
    def build_knowledge_graph(self, analysis_facts: Dict[str, Any]) -> Dict[str, Any]:
        """Transforms raw static analysis outputs into a unified repository knowledge graph."""
        file_tree = analysis_facts.get("file_tree", [])
        parsed_files = analysis_facts.get("parsed_files", {})
        dependencies = analysis_facts.get("dependencies", {})
        frameworks = analysis_facts.get("frameworks", [])
        build_tools = analysis_facts.get("build_tools", [])
        
        # 1. Normalize modules (parsed files)
        modules = {}
        for path, facts in parsed_files.items():
            modules[path] = {
                "name": os.path.basename(path),
                "path": path,
                "lines_of_code": facts.get("lines_of_code", 0),
                "classes": facts.get("classes", []),
                "functions": facts.get("functions", []),
                "raw_imports": facts.get("imports", []),
                "resolved_imports": []
            }
            
        # 2. Resolve module imports (construct dependency edges)
        self._resolve_module_imports(modules, file_tree)

        # 3. Detect services/logical boundaries
        services = self._detect_service_boundaries(modules, file_tree)

        # 4. Synthesize logical layers (e.g. Database, API, Middleware, Frontend, Utils)
        layers = self._group_into_architectural_layers(modules)

        # 5. Create nodes and edges for the unified graph representation
        graph_nodes = []
        graph_edges = []

        # Config files as nodes
        for config_path in analysis_facts.get("config_files", []):
            graph_nodes.append({
                "id": f"config:{config_path}",
                "name": os.path.basename(config_path),
                "type": "configuration",
                "properties": {
                    "path": config_path
                }
            })

        # Service nodes
        for service_name, service_data in services.items():
            graph_nodes.append({
                "id": f"service:{service_name}",
                "name": service_name,
                "type": "service",
                "properties": {
                    "description": service_data["description"],
                    "path_prefix": service_data["prefix"]
                }
            })

        # Layer nodes
        for layer_name, file_paths in layers.items():
            graph_nodes.append({
                "id": f"layer:{layer_name}",
                "name": layer_name,
                "type": "architectural_layer",
                "properties": {
                    "module_count": len(file_paths)
                }
            })

        # Module nodes
        for path, mod in modules.items():
            graph_nodes.append({
                "id": f"module:{path}",
                "name": mod["name"],
                "type": "module",
                "properties": {
                    "path": path,
                    "loc": mod["lines_of_code"],
                    "functions_count": len(mod["functions"]),
                    "classes_count": len(mod["classes"])
                }
            })

            # Edge: module -> service (PART_OF)
            for service_name, service_data in services.items():
                if path.startswith(service_data["prefix"]):
                    graph_edges.append({
                        "source": f"module:{path}",
                        "target": f"service:{service_name}",
                        "relation": "PART_OF"
                    })
                    break

            # Edge: module -> layer (BELONGS_TO)
            for layer_name, file_paths in layers.items():
                if path in file_paths:
                    graph_edges.append({
                        "source": f"module:{path}",
                        "target": f"layer:{layer_name}",
                        "relation": "BELONGS_TO"
                    })
                    break

            # Edge: module -> module (IMPORTS)
            for target_import in mod["resolved_imports"]:
                graph_edges.append({
                    "source": f"module:{path}",
                    "target": f"module:{target_import}",
                    "relation": "IMPORTS"
                })

        return {
            "metadata": {
                "frameworks": frameworks,
                "build_tools": build_tools,
                "dependencies": dependencies
            },
            "nodes": graph_nodes,
            "edges": graph_edges,
            "modules": modules,
            "services": services,
            "layers": layers
        }

    def _resolve_module_imports(self, modules: Dict[str, Dict[str, Any]], file_tree: List[str]):
        """Attempts to match raw import statements in modules to valid files in the file_tree."""
        file_tree_set = set(file_tree)
        
        for path, mod in modules.items():
            dir_name = os.path.dirname(path)
            for raw_imp in mod["raw_imports"]:
                # Try to extract the imported module name
                # Python: "from x.y import z" or "import a"
                # JS/TS: "import x from '../y'" or "const x = require('./z')"
                imported_rel_path = ""
                
                # Check for JS/TS import path in quotes
                quotes_match = re.search(r'[\'"]([^\'"]+)[\'"]', raw_imp)
                if quotes_match:
                    imported_rel_path = quotes_match.group(1)
                else:
                    # Check for Python style imports
                    py_match = re.search(r'(?:from|import)\s+(\w+(?:\.\w+)*)', raw_imp)
                    if py_match:
                        imported_rel_path = py_match.group(1).replace(".", "/")

                if not imported_rel_path:
                    continue

                # 1. Check relative resolution (e.g. ./y or ../y)
                resolved = False
                if imported_rel_path.startswith("."):
                    # Resolve path traversal
                    candidate = os.path.normpath(os.path.join(dir_name, imported_rel_path)).replace("\\", "/")
                    # Try checking exact extensions
                    for ext in [".ts", ".tsx", ".js", ".jsx", ".py"]:
                        if f"{candidate}{ext}" in file_tree_set:
                            mod["resolved_imports"].append(f"{candidate}{ext}")
                            resolved = True
                            break
                        if f"{candidate}/index{ext}" in file_tree_set:
                            mod["resolved_imports"].append(f"{candidate}/index{ext}")
                            resolved = True
                            break
                            
                # 2. Check absolute/base resolution
                if not resolved:
                    # Look for imported module relative to project root (e.g. absolute imports)
                    for ext in [".ts", ".tsx", ".js", ".jsx", ".py", ""]:
                        test_path = f"{imported_rel_path}{ext}" if ext else imported_rel_path
                        if test_path in file_tree_set:
                            mod["resolved_imports"].append(test_path)
                            resolved = True
                            break
                        # e.g., src/auth
                        test_src_path = f"src/{imported_rel_path}{ext}"
                        if test_src_path in file_tree_set:
                            mod["resolved_imports"].append(test_src_path)
                            resolved = True
                            break
            
            # De-duplicate and sort
            mod["resolved_imports"] = sorted(list(set(mod["resolved_imports"])))

    def _detect_service_boundaries(self, modules: Dict[str, Any], file_tree: List[str]) -> Dict[str, Dict[str, str]]:
        """Identifies logical services and folders boundaries based on folder hierarchy."""
        services = {}
        
        # Look for common service folders
        possible_prefixes = [
            ("api", "app/api", "HTTP API Routes Layer"),
            ("api_v2", "api/", "Backend API Gateway"),
            ("components", "src/components", "Frontend Shared UI Components"),
            ("components_next", "app/components", "NextJS Page Components"),
            ("agents", "backend/app/agents", "Agentic Orchestration Logic"),
            ("models", "models/", "ML Inference Models"),
            ("database", "db/", "Database Schema and Migrations"),
            ("services", "services/", "Application Core Services"),
        ]

        # Scan actual file tree to confirm folders exist
        file_tree_paths = sorted(list(set(os.path.dirname(f) for f in file_tree)))
        for name, prefix, desc in possible_prefixes:
            for path in file_tree_paths:
                if path.startswith(prefix):
                    services[name] = {"prefix": prefix, "description": desc}
                    break
                    
        # Add a default fallback service for root modules
        if not services:
            services["core"] = {"prefix": "", "description": "Core Application Logic"}

        return services

    def _group_into_architectural_layers(self, modules: Dict[str, Any]) -> Dict[str, List[str]]:
        """Groups modules into standard architectural layers based on filenames and import structures."""
        layers = {
            "Database": [],
            "Routing/API": [],
            "Middleware": [],
            "Frontend UI": [],
            "Utilities": [],
            "Other": []
        }

        for path, mod in modules.items():
            name = mod["name"].lower()
            
            if any(term in name for term in ["db", "database", "model", "schema", "entity", "repository"]):
                layers["Database"].append(path)
            elif any(term in name for term in ["route", "controller", "api", "endpoint", "views"]):
                layers["Routing/API"].append(path)
            elif any(term in name for term in ["middleware", "auth", "guard", "session"]):
                layers["Middleware"].append(path)
            elif any(term in name for term in ["component", "page", "style", "css", "tshtml", "jsx", "tsx"]):
                layers["Frontend UI"].append(path)
            elif any(term in name for term in ["utils", "helpers", "lib", "common", "config"]):
                layers["Utilities"].append(path)
            else:
                layers["Other"].append(path)

        return layers
