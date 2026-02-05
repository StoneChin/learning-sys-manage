"""Neo4j 知识图谱查询服务：为前端提供图数据、节点搜索、路径查询；与 LightRAG 使用的 workspace（kb_id）一致。"""
from typing import List, Dict, Any, Optional

from config import settings


def _driver():
    """同步 Neo4j 驱动，按需创建。"""
    from neo4j import GraphDatabase
    return GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
    )


def _workspace_label(kb_id: int) -> str:
    """LightRAG 使用的 workspace 即 str(kb_id)。"""
    return str(kb_id)


def get_graph(kb_id: int, limit: int = 500) -> Dict[str, Any]:
    """获取知识图谱的节点与边，供前端可视化。"""
    label = _workspace_label(kb_id)
    driver = _driver()
    try:
        with driver.session(database=settings.NEO4J_DATABASE) as session:
            nodes_result = session.run(
                f"MATCH (n:`{label}`) RETURN n LIMIT $limit",
                limit=limit,
            )
            nodes = []
            seen = set()
            for record in nodes_result:
                n = record["n"]
                eid = n.get("entity_id")
                if eid and eid not in seen:
                    seen.add(eid)
                    nodes.append({
                        "id": eid,
                        "name": eid,
                        **{k: v for k, v in dict(n).items() if k != "entity_id"},
                    })
            edges_result = session.run(
                f"MATCH (a:`{label}`)-[r]-(b:`{label}`) "
                "RETURN DISTINCT a.entity_id AS source, b.entity_id AS target LIMIT $limit",
                limit=limit,
            )
            edges = []
            for record in edges_result:
                edges.append({
                    "source": record["source"],
                    "target": record["target"],
                })
            return {"nodes": nodes, "edges": edges}
    finally:
        driver.close()


def query_nodes(kb_id: int, keyword: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """按关键词搜索节点（entity_id CONTAINS）。"""
    label = _workspace_label(kb_id)
    driver = _driver()
    try:
        with driver.session(database=settings.NEO4J_DATABASE) as session:
            if keyword and keyword.strip():
                result = session.run(
                    f"MATCH (n:`{label}`) WHERE n.entity_id CONTAINS $kw RETURN n LIMIT $limit",
                    kw=keyword.strip(),
                    limit=limit,
                )
            else:
                result = session.run(
                    f"MATCH (n:`{label}`) RETURN n LIMIT $limit",
                    limit=limit,
                )
            nodes = []
            for record in result:
                n = record["n"]
                eid = n.get("entity_id")
                if eid:
                    nodes.append({"id": eid, "name": eid, **dict(n)})
            return nodes
    finally:
        driver.close()


def query_path(
    kb_id: int,
    from_name: str,
    to_name: str,
    max_depth: int = 10,
) -> Dict[str, Any]:
    """两节点间最短路径。"""
    label = _workspace_label(kb_id)
    driver = _driver()
    try:
        with driver.session(database=settings.NEO4J_DATABASE) as session:
            # 使用 shortestPath，限制深度
            q = f"""
            MATCH (a:`{label}` {{entity_id: $from_id}}), (b:`{label}` {{entity_id: $to_id}})
            MATCH path = shortestPath((a)-[*..{max_depth}]-(b))
            RETURN path
            """
            result = session.run(q, from_id=from_name.strip(), to_id=to_name.strip())
            record = result.single()
            if not record or not record.get("path"):
                return {"nodes": [], "edges": [], "found": False}
            path = record["path"]
            nodes = [{"id": n.get("entity_id"), "name": n.get("entity_id")} for n in path.nodes if n.get("entity_id")]
            edges = [
                {"source": rel.start_node.get("entity_id"), "target": rel.end_node.get("entity_id")}
                for rel in path.relationships
            ]
            return {"nodes": nodes, "edges": edges, "found": True}
    finally:
        driver.close()


def delete_workspace(kb_id: int) -> None:
    """删除该知识库在 Neo4j 中的图数据（与 LightRAG 的 workspace 一致）。"""
    label = _workspace_label(kb_id)
    driver = _driver()
    try:
        with driver.session(database=settings.NEO4J_DATABASE) as session:
            session.run(f"MATCH (n:`{label}`) DETACH DELETE n")
    finally:
        driver.close()
