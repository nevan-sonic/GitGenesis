from abc import ABC, abstractmethod
import json
from typing import List, Dict, Any, Optional
from app.database import get_db_connection

class GraphRepository(ABC):
    @abstractmethod
    def create_blueprint(self, blueprint_id: str, repository_id: int, name: str, user_id: Optional[str] = None) -> None:
        pass

    @abstractmethod
    def create_branch(self, branch_id: str, blueprint_id: str, name: str, active: bool = False) -> None:
        pass

    @abstractmethod
    def get_active_branch(self, blueprint_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def set_active_branch(self, blueprint_id: str, branch_id: str) -> None:
        pass

    @abstractmethod
    def add_node(self, node_id: str, blueprint_id: str, branch_id: str, name: str, node_type: str, 
                 confidence_score: int, supporting_evidence: List[str], architectural_reasoning_summary: str,
                 source_files: List[str], dependency_references: List[str], related_modules: List[str], 
                 generated_task: str, embedding: Optional[List[float]] = None, status: str = 'todo',
                 confidence_explanation: Optional[str] = None) -> None:
        pass

    @abstractmethod
    def add_edge(self, edge_id: str, blueprint_id: str, branch_id: str, source_id: str, target_id: str, 
                 relation_type: str) -> None:
        pass

    @abstractmethod
    def get_nodes(self, blueprint_id: str, branch_id: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_edges(self, blueprint_id: str, branch_id: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_node(self, node_id: str, branch_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def update_node(self, node_id: str, branch_id: str, **kwargs) -> None:
        pass

    @abstractmethod
    def get_descendants(self, blueprint_id: str, branch_id: str, start_node_id: str) -> List[str]:
        pass

    @abstractmethod
    def get_ancestors(self, blueprint_id: str, branch_id: str, start_node_id: str) -> List[str]:
        pass

    @abstractmethod
    def vector_search_nodes(self, blueprint_id: str, branch_id: str, query_embedding: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def clone_branch(self, source_branch_id: str, target_branch_id: str, new_name: str) -> None:
        pass

    @abstractmethod
    def save_modified_file(self, blueprint_id: str, branch_id: str, file_path: str, content: str) -> None:
        pass

    @abstractmethod
    def get_modified_files(self, blueprint_id: str, branch_id: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def delete_node(self, node_id: str, branch_id: str) -> None:
        pass

    @abstractmethod
    def delete_edge(self, edge_id: str, branch_id: str) -> None:
        pass


class PostgresGraphRepository(GraphRepository):
    def create_blueprint(self, blueprint_id: str, repository_id: int, name: str, user_id: Optional[str] = None) -> None:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO executable_blueprints (id, repository_id, name, user_id)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING;
                """, (blueprint_id, repository_id, name, user_id))
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def create_branch(self, branch_id: str, blueprint_id: str, name: str, active: bool = False) -> None:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                if active:
                    # Set other branches for this blueprint inactive
                    cur.execute("""
                        UPDATE branches SET active = FALSE WHERE blueprint_id = %s;
                    """, (blueprint_id,))
                cur.execute("""
                    INSERT INTO branches (id, blueprint_id, name, active)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING;
                """, (branch_id, blueprint_id, name, active))
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_active_branch(self, blueprint_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, blueprint_id, name, active FROM branches
                    WHERE blueprint_id = %s AND active = TRUE
                    LIMIT 1;
                """, (blueprint_id,))
                return cur.fetchone()
        finally:
            conn.close()

    def set_active_branch(self, blueprint_id: str, branch_id: str) -> None:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE branches SET active = FALSE WHERE blueprint_id = %s;
                """, (blueprint_id,))
                cur.execute("""
                    UPDATE branches SET active = TRUE WHERE id = %s;
                """, (branch_id,))
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def add_node(self, node_id: str, blueprint_id: str, branch_id: str, name: str, node_type: str, 
                 confidence_score: int, supporting_evidence: List[str], architectural_reasoning_summary: str,
                 source_files: List[str], dependency_references: List[str], related_modules: List[str], 
                 generated_task: str, embedding: Optional[List[float]] = None, status: str = 'todo',
                 confidence_explanation: Optional[str] = None) -> None:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO executable_blueprint_nodes (
                        id, blueprint_id, branch_id, name, type, confidence_score, confidence_explanation,
                        supporting_evidence, architectural_reasoning_summary, 
                        source_files, dependency_references, related_modules, 
                        generated_task, embedding, status
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    ) ON CONFLICT (id, branch_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        type = EXCLUDED.type,
                        confidence_score = EXCLUDED.confidence_score,
                        confidence_explanation = EXCLUDED.confidence_explanation,
                        supporting_evidence = EXCLUDED.supporting_evidence,
                        architectural_reasoning_summary = EXCLUDED.architectural_reasoning_summary,
                        source_files = EXCLUDED.source_files,
                        dependency_references = EXCLUDED.dependency_references,
                        related_modules = EXCLUDED.related_modules,
                        generated_task = EXCLUDED.generated_task,
                        embedding = COALESCE(EXCLUDED.embedding, executable_blueprint_nodes.embedding),
                        status = COALESCE(EXCLUDED.status, executable_blueprint_nodes.status);
                """, (
                    node_id, blueprint_id, branch_id, name, node_type, confidence_score,
                    confidence_explanation, json.dumps(supporting_evidence), architectural_reasoning_summary,
                    json.dumps(source_files), json.dumps(dependency_references), json.dumps(related_modules),
                    generated_task, embedding, status
                ))
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def add_edge(self, edge_id: str, blueprint_id: str, branch_id: str, source_id: str, target_id: str, 
                 relation_type: str) -> None:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO executable_blueprint_edges (id, blueprint_id, branch_id, source_id, target_id, relation_type)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id, branch_id) DO UPDATE SET
                        source_id = EXCLUDED.source_id,
                        target_id = EXCLUDED.target_id,
                        relation_type = EXCLUDED.relation_type;
                """, (edge_id, blueprint_id, branch_id, source_id, target_id, relation_type))
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_nodes(self, blueprint_id: str, branch_id: str) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, blueprint_id, branch_id, name, type, confidence_score, confidence_explanation,
                           supporting_evidence, architectural_reasoning_summary, 
                           source_files, dependency_references, related_modules, 
                           generated_task, status FROM executable_blueprint_nodes
                    WHERE blueprint_id = %s AND branch_id = %s;
                """, (blueprint_id, branch_id))
                return cur.fetchall()
        finally:
            conn.close()

    def get_edges(self, blueprint_id: str, branch_id: str) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, blueprint_id, branch_id, source_id, target_id, relation_type 
                    FROM executable_blueprint_edges
                    WHERE blueprint_id = %s AND branch_id = %s;
                """, (blueprint_id, branch_id))
                return cur.fetchall()
        finally:
            conn.close()

    def get_node(self, node_id: str, branch_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, blueprint_id, branch_id, name, type, confidence_score, confidence_explanation,
                           supporting_evidence, architectural_reasoning_summary, 
                           source_files, dependency_references, related_modules, 
                           generated_task, status FROM executable_blueprint_nodes
                    WHERE id = %s AND branch_id = %s;
                """, (node_id, branch_id))
                return cur.fetchone()
        finally:
            conn.close()

    def update_node(self, node_id: str, branch_id: str, **kwargs) -> None:
        if not kwargs:
            return
        
        # Filter for valid fields to update
        valid_fields = {
            'name', 'type', 'confidence_score', 'supporting_evidence', 
            'architectural_reasoning_summary', 'source_files', 
            'dependency_references', 'related_modules', 'generated_task', 'embedding', 'status'
        }
        
        updates = []
        params = []
        for key, val in kwargs.items():
            if key in valid_fields:
                updates.append(f"{key} = %s")
                if key in ('supporting_evidence', 'source_files', 'dependency_references', 'related_modules') and isinstance(val, (list, dict)):
                    params.append(json.dumps(val))
                else:
                    params.append(val)
                    
        if not updates:
            return
            
        params.extend([node_id, branch_id])
        query = f"""
            UPDATE executable_blueprint_nodes
            SET {', '.join(updates)}
            WHERE id = %s AND branch_id = %s;
        """
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_descendants(self, blueprint_id: str, branch_id: str, start_node_id: str) -> List[str]:
        """Fetches all descendant nodes (downstream dependencies) of start_node_id using a recursive CTE."""
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    WITH RECURSIVE downstream AS (
                        -- Anchor member: direct targets of start_node_id
                        SELECT target_id AS node_id
                        FROM executable_blueprint_edges
                        WHERE source_id = %s AND branch_id = %s
                        
                        UNION
                        
                        -- Recursive member: nodes depending on already identified downstream nodes
                        SELECT e.target_id
                        FROM executable_blueprint_edges e
                        INNER JOIN downstream d ON e.source_id = d.node_id
                        WHERE e.branch_id = %s
                    )
                    SELECT node_id FROM downstream;
                """, (start_node_id, branch_id, branch_id))
                rows = cur.fetchall()
                return [row['node_id'] for row in rows]
        finally:
            conn.close()

    def get_ancestors(self, blueprint_id: str, branch_id: str, start_node_id: str) -> List[str]:
        """Fetches all ancestor nodes (upstream requirements) of start_node_id using a recursive CTE."""
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    WITH RECURSIVE upstream AS (
                        -- Anchor member: direct sources/prerequisites of start_node_id
                        SELECT source_id AS node_id
                        FROM executable_blueprint_edges
                        WHERE target_id = %s AND branch_id = %s
                        
                        UNION
                        
                        -- Recursive member: sources of already identified upstream nodes
                        SELECT e.source_id
                        FROM executable_blueprint_edges e
                        INNER JOIN upstream u ON e.target_id = u.node_id
                        WHERE e.branch_id = %s
                    )
                    SELECT node_id FROM upstream;
                """, (start_node_id, branch_id, branch_id))
                rows = cur.fetchall()
                return [row['node_id'] for row in rows]
        finally:
            conn.close()

    def vector_search_nodes(self, blueprint_id: str, branch_id: str, query_embedding: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # pgvector cosine distance is <=> operator
                cur.execute("""
                    SELECT id, blueprint_id, branch_id, name, type, confidence_score, confidence_explanation,
                           supporting_evidence, architectural_reasoning_summary, 
                           source_files, dependency_references, related_modules, 
                           generated_task, (embedding <=> %s) AS distance
                    FROM executable_blueprint_nodes
                    WHERE blueprint_id = %s AND branch_id = %s AND embedding IS NOT NULL
                    ORDER BY distance ASC
                    LIMIT %s;
                """, (query_embedding, blueprint_id, branch_id, limit))
                return cur.fetchall()
        except Exception as e:
            print(f"Vector search failed (pgvector might not be enabled): {e}")
            # Fallback to standard textual search if vector query fails
            return []
        finally:
            conn.close()

    def clone_branch(self, source_branch_id: str, target_branch_id: str, new_name: str) -> None:
        """Clones all nodes and edges from a source branch to a new target branch."""
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Get details of source branch to match blueprint_id
                cur.execute("SELECT blueprint_id FROM branches WHERE id = %s;", (source_branch_id,))
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"Source branch {source_branch_id} not found.")
                blueprint_id = row['blueprint_id']

                # Create the target branch record
                cur.execute("""
                    INSERT INTO branches (id, blueprint_id, name, active)
                    VALUES (%s, %s, %s, FALSE)
                    ON CONFLICT (id) DO NOTHING;
                """, (target_branch_id, blueprint_id, new_name))

                # Clone nodes
                cur.execute("""
                    INSERT INTO executable_blueprint_nodes (
                        id, blueprint_id, branch_id, name, type, confidence_score, confidence_explanation,
                        supporting_evidence, architectural_reasoning_summary, 
                        source_files, dependency_references, related_modules, 
                        generated_task, embedding, status
                    )
                    SELECT 
                        id, blueprint_id, %s, name, type, confidence_score, confidence_explanation,
                        supporting_evidence, architectural_reasoning_summary, 
                        source_files, dependency_references, related_modules, 
                        generated_task, embedding, status
                    FROM executable_blueprint_nodes
                    WHERE branch_id = %s;
                """, (target_branch_id, source_branch_id))

                # Clone edges
                cur.execute("""
                    INSERT INTO executable_blueprint_edges (id, blueprint_id, branch_id, source_id, target_id, relation_type)
                    SELECT id, blueprint_id, %s, source_id, target_id, relation_type
                    FROM executable_blueprint_edges
                    WHERE branch_id = %s;
                """, (target_branch_id, source_branch_id))

                # Clone modified files
                cur.execute("""
                    INSERT INTO modified_files (blueprint_id, branch_id, file_path, content)
                    SELECT blueprint_id, %s, file_path, content
                    FROM modified_files
                    WHERE branch_id = %s;
                """, (target_branch_id, source_branch_id))

                conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def save_modified_file(self, blueprint_id: str, branch_id: str, file_path: str, content: str) -> None:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO modified_files (blueprint_id, branch_id, file_path, content)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (blueprint_id, branch_id, file_path) 
                    DO UPDATE SET content = EXCLUDED.content;
                """, (blueprint_id, branch_id, file_path, content))
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_modified_files(self, blueprint_id: str, branch_id: str) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT file_path, content FROM modified_files
                    WHERE blueprint_id = %s AND branch_id = %s;
                """, (blueprint_id, branch_id))
                return cur.fetchall()
        finally:
            conn.close()

    def delete_node(self, node_id: str, branch_id: str) -> None:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # First delete edges involving this node
                cur.execute("""
                    DELETE FROM executable_blueprint_edges 
                    WHERE branch_id = %s AND (source_id = %s OR target_id = %s);
                """, (branch_id, node_id, node_id))
                # Delete the node itself
                cur.execute("""
                    DELETE FROM executable_blueprint_nodes 
                    WHERE id = %s AND branch_id = %s;
                """, (node_id, branch_id))
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def delete_edge(self, edge_id: str, branch_id: str) -> None:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM executable_blueprint_edges 
                    WHERE id = %s AND branch_id = %s;
                """, (edge_id, branch_id))
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
