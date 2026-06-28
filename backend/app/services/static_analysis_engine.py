import os
import re
from typing import List, Dict, Any, Optional
from tree_sitter_languages import get_parser

class StaticAnalysisEngine:
    def __init__(self):
        # Initialize tree-sitter parsers
        self.parsers = {}
        for lang in ["python", "javascript", "typescript"]:
            try:
                self.parsers[lang] = get_parser(lang)
            except Exception as e:
                print(f"Warning: Tree-sitter parser for {lang} failed to initialize: {e}")

    def analyze_repository(self, repo_path: str) -> Dict[str, Any]:
        """Performs deterministic static analysis on a local repository path."""
        print(f"Starting static analysis for {repo_path}...")
        
        # 1. Discover configuration files and detect frameworks/build tools
        config_files = self._discover_configs(repo_path)
        dependencies = self._extract_dependencies(repo_path, config_files)
        frameworks, build_tools = self._detect_frameworks_and_tools(config_files, dependencies)
        
        # 2. Parse README files
        readme_content = self._parse_readme(repo_path)
        
        # 3. Analyze source files (AST & Imports)
        file_tree = []
        parsed_files = {}
        
        # Traverse repository
        for root, dirs, files in os.walk(repo_path):
            # Skip noise directories
            dirs[:] = [d for d in dirs if d not in {
                '.git', 'node_modules', 'venv', '.venv', 'dist', 'build', 
                '.next', '.gemini', '__pycache__', 'out'
            }]
            dirs.sort()
            files.sort()
            
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, repo_path).replace("\\", "/")
                file_tree.append(rel_path)
                
                # Check if it is a source file of interest
                ext = os.path.splitext(file)[1].lower()
                if ext in {'.py', '.js', '.jsx', '.ts', '.tsx'}:
                    file_facts = self._analyze_source_file(full_path, ext)
                    if file_facts:
                        parsed_files[rel_path] = file_facts

        file_tree.sort()
        sorted_parsed_files = {k: parsed_files[k] for k in sorted(parsed_files.keys())}

        return {
            "file_tree": file_tree,
            "config_files": sorted(config_files),
            "dependencies": dependencies,
            "frameworks": frameworks,
            "build_tools": build_tools,
            "readme": readme_content,
            "parsed_files": sorted_parsed_files
        }

    def _discover_configs(self, repo_path: str) -> List[str]:
        config_names = {
            'package.json', 'tsconfig.json', 'requirements.txt', 'pyproject.toml', 
            'setup.py', 'go.mod', 'cargo.toml', 'dockerfile', 'docker-compose.yml',
            'next.config.js', 'next.config.mjs', 'vite.config.ts', 'vite.config.js'
        }
        found_configs = []
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', 'venv', '.venv'}]
            dirs.sort()
            files.sort()
            for file in files:
                if file.lower() in config_names:
                    rel_path = os.path.relpath(os.path.join(root, file), repo_path).replace("\\", "/")
                    found_configs.append(rel_path)
        return sorted(found_configs)

    def _extract_dependencies(self, repo_path: str, config_files: List[str]) -> Dict[str, List[str]]:
        dependencies = {"npm": [], "python": [], "other": []}
        
        for config in config_files:
            full_path = os.path.join(repo_path, config)
            if config.endswith("package.json"):
                try:
                    import json
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        data = json.load(f)
                        deps = data.get("dependencies", {})
                        dev_deps = data.get("devDependencies", {})
                        dependencies["npm"].extend(list(deps.keys()) + list(dev_deps.keys()))
                except Exception as e:
                    print(f"Error parsing package.json dependencies: {e}")
                    
            elif config.endswith("requirements.txt"):
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#"):
                                # Extract package name before any operators (==, >=, etc.)
                                name = re.split(r'[<>=~#]', line)[0].strip()
                                if name:
                                    dependencies["python"].append(name)
                except Exception as e:
                    print(f"Error parsing requirements.txt dependencies: {e}")
                    
            elif config.endswith("pyproject.toml"):
                try:
                    import tomllib  # Python 3.11+
                except ImportError:
                    # Quick regex fallback if tomllib not available
                    tomllib = None
                
                if tomllib:
                    try:
                        with open(full_path, "rb") as f:
                            data = tomllib.load(f)
                            # poetry
                            poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
                            dependencies["python"].extend(list(poetry_deps.keys()))
                            # standard project dependencies
                            project_deps = data.get("project", {}).get("dependencies", [])
                            dependencies["python"].extend(project_deps)
                    except Exception as e:
                        print(f"Error parsing pyproject.toml: {e}")
                else:
                    # Simple text read fallback
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            # Find standard dependency declarations
                            deps = re.findall(r'dependencies\s*=\s*\[(.*?)\]', content, re.DOTALL)
                            for dep_block in deps:
                                for name in re.findall(r'"([^"]+)"', dep_block):
                                    dependencies["python"].append(name.split(";")[0].strip())
                    except Exception as e:
                        print(f"Regex parsing fallback for pyproject.toml failed: {e}")
        dependencies["npm"] = sorted(list(set(dependencies["npm"])))
        dependencies["python"] = sorted(list(set(dependencies["python"])))
        dependencies["other"] = sorted(list(set(dependencies["other"])))
        return dependencies

    def _detect_frameworks_and_tools(self, config_files: List[str], dependencies: Dict[str, List[str]]) -> tuple:
        frameworks = set()
        build_tools = set()
        
        all_deps = set(dependencies["npm"] + dependencies["python"])
        
        # Check npm packages
        npm_framework_map = {
            "next": "Next.js", "react": "React", "vue": "Vue", "svelte": "Svelte", 
            "express": "Express", "fastify": "Fastify", "nuxt": "Nuxt.js", "sveltekit": "SvelteKit"
        }
        for dep, val in npm_framework_map.items():
            if dep in all_deps:
                frameworks.add(val)
                
        # Check python packages
        py_framework_map = {
            "fastapi": "FastAPI", "django": "Django", "flask": "Flask", 
            "tornado": "Tornado", "sqlalchemy": "SQLAlchemy"
        }
        for dep, val in py_framework_map.items():
            if dep in all_deps:
                frameworks.add(val)

        # Check config files
        for config in config_files:
            if "next.config" in config:
                frameworks.add("Next.js")
            if "vite.config" in config:
                build_tools.add("Vite")
            if "go.mod" in config:
                build_tools.add("Go Build")
            if "cargo.toml" in config:
                build_tools.add("Cargo")
                
        return sorted(list(frameworks)), sorted(list(build_tools))

    def _parse_readme(self, repo_path: str) -> str:
        for file in os.listdir(repo_path):
            if file.lower() == "readme.md":
                try:
                    with open(os.path.join(repo_path, file), "r", encoding="utf-8", errors="ignore") as f:
                        return f.read()
                except Exception as e:
                    print(f"Error reading README.md: {e}")
        return ""

    def _analyze_source_file(self, file_path: str, ext: str) -> Optional[Dict[str, Any]]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                code = f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None

        imports = []
        classes = []
        functions = []

        # Choose tree-sitter parser
        lang_key = "python" if ext == ".py" else ("typescript" if ext in {".ts", ".tsx"} else "javascript")
        parser = self.parsers.get(lang_key)

        if parser:
            try:
                tree = parser.parse(bytes(code, "utf8"))
                root_node = tree.root_node
                self._traverse_ast(root_node, imports, classes, functions, code)
            except Exception as e:
                print(f"Tree-sitter AST parse failed for {file_path}, falling back to regex: {e}")
                self._regex_ast_fallback(code, ext, imports, classes, functions)
        else:
            # Fallback to regex parser if tree-sitter isn't loaded
            self._regex_ast_fallback(code, ext, imports, classes, functions)

        return {
            "imports": sorted(list(set(imports))),
            "classes": sorted(list(set(classes))),
            "functions": sorted(list(set(functions))),
            "lines_of_code": len(code.splitlines())
        }

    def _traverse_ast(self, node, imports: list, classes: list, functions: list, code: str):
        # Extract imports, class names, function names
        node_type = node.type
        
        if node_type == "import_statement" or node_type == "import_from_statement":
            # Python import
            imports.append(code[node.start_byte:node.end_byte])
        elif node_type in {"import_declaration", "lexical_declaration", "variable_declarator"}:
            # JS/TS import or require
            stmt = code[node.start_byte:node.end_byte]
            if "import " in stmt or "require(" in stmt:
                imports.append(stmt)
                
        elif node_type == "class_definition" or node_type == "class_declaration":
            # Find class name
            for child in node.children:
                if child.type == "identifier":
                    classes.append(code[child.start_byte:child.end_byte])
                    break
        elif node_type in {"function_definition", "function_declaration", "method_definition"}:
            # Find function name
            for child in node.children:
                if child.type == "identifier":
                    functions.append(code[child.start_byte:child.end_byte])
                    break
                    
        # Traverse children
        for child in node.children:
            self._traverse_ast(child, imports, classes, functions, code)

    def _regex_ast_fallback(self, code: str, ext: str, imports: list, classes: list, functions: list):
        # Simple regex matcher fallback
        if ext == ".py":
            # Python imports
            for match in re.finditer(r'^\s*(import \w+|from \w+ import \w+)', code, re.MULTILINE):
                imports.append(match.group(1))
            # Classes
            for match in re.finditer(r'^\s*class (\w+)', code, re.MULTILINE):
                classes.append(match.group(1))
            # Functions
            for match in re.finditer(r'^\s*def (\w+)', code, re.MULTILINE):
                functions.append(match.group(1))
        else:
            # JS/TS imports
            for match in re.finditer(r'^\s*(import\s+.*?\s+from\s+[\'"].*?[\'"]|const\s+.*?\s*=\s*require\([\'"].*?[\'"]\))', code, re.MULTILINE):
                imports.append(match.group(1))
            # Classes
            for match in re.finditer(r'^\s*class (\w+)', code, re.MULTILINE):
                classes.append(match.group(1))
            # Functions
            for match in re.finditer(r'^\s*(?:async\s+)?function\s+(\w+)', code, re.MULTILINE):
                functions.append(match.group(1))
            for match in re.finditer(r'^\s*(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>', code, re.MULTILINE):
                functions.append(match.group(1))
