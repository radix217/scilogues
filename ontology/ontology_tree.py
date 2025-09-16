from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Iterable, Dict, Any, Tuple
import os
import pickle
import networkx as nx
from generator import expand
from flask_socketio import SocketIO

ROOT_TOPIC = "Knowledge"


@dataclass
class Node:
    id: str
    topic: str
    parentid: Optional[str]
    expanded: str = "false"
    depth: int = 0
    importance: int = 0


@dataclass
class Edge:
    parentid: str
    childid: str
    relation: str = "is_a"
    order: int = 0


def normalize_expanded(v: Any) -> str:
    if isinstance(v, str):
        s = v.strip().lower()
        if s in {"true", "false", "skipped"}:
            return s
    if isinstance(v, bool):
        return "true" if v else "false"
    s = str(v).strip().lower()
    if s in {"1", "true", "t", "yes", "y"}:
        return "true"
    if s in {"0", "false", "f", "no", "n", ""}:
        return "false"
    return "false"


def graph_path_from_csv(csv_path: str) -> str:
    base, _ = os.path.splitext(csv_path)
    if base.endswith("_edges"):
        base = base[: -len("_edges")]
    return base + ".pkl"


def ensure_parent_dir(path: str) -> None:
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def load_graph(csv_path: str) -> nx.DiGraph:
    gpath = graph_path_from_csv(csv_path)
    if os.path.exists(gpath) and os.path.getsize(gpath) > 0:
        try:
            with open(gpath, "rb") as f:
                G = pickle.load(f)
            if not isinstance(G, nx.DiGraph):
                G = nx.DiGraph(G)
            return G
        except Exception:
            pass
    return nx.DiGraph()


def persist_graph(G: nx.DiGraph, csv_path: str) -> None:
    gpath = graph_path_from_csv(csv_path)
    ensure_parent_dir(gpath)
    with open(gpath, "wb") as f:
        pickle.dump(G, f, protocol=pickle.HIGHEST_PROTOCOL)


def nodes_from_graph(G: nx.DiGraph) -> List[Node]:
    nodes: List[Node] = []
    for nid, data in G.nodes(data=True):
        nodes.append(
            Node(
                id=str(nid),
                topic=str(data.get("topic", "")),
                parentid=data.get("parentid"),
                expanded=normalize_expanded(data.get("expanded", "false")),
                depth=int(data.get("depth", 0) or 0),
                importance=int(data.get("importance", 0) or 0),
            )
        )
    return nodes


def edges_from_graph(G: nx.DiGraph) -> List[Edge]:
    edges: List[Edge] = []
    for u, v, data in G.edges(data=True):
        edges.append(
            Edge(
                parentid=str(u),
                childid=str(v),
                relation=str(data.get("relation", "is_a") or "is_a"),
                order=int(data.get("order", 0) or 0),
            )
        )
    return edges


def read_nodes(csv_path: str) -> List[Node]:
    G = load_graph(csv_path)
    return nodes_from_graph(G)


def read_edges(csv_path: str) -> List[Edge]:
    G = load_graph(csv_path)
    return edges_from_graph(G)


def write_nodes(csv_path: str, nodes: List[Node]) -> None:
    G = load_graph(csv_path)
    for n in nodes:
        if not G.has_node(n.id):
            G.add_node(n.id)
        G.nodes[n.id]["topic"] = n.topic
        G.nodes[n.id]["parentid"] = n.parentid
        G.nodes[n.id]["expanded"] = normalize_expanded(getattr(n, "expanded", "false"))
        G.nodes[n.id]["depth"] = int(getattr(n, "depth", 0) or 0)
        G.nodes[n.id]["importance"] = int(getattr(n, "importance", 0) or 0)
    persist_graph(G, csv_path)


def write_edges(csv_path: str, edges: List[Edge]) -> None:
    G = load_graph(csv_path)
    for e in edges:
        if not G.has_node(e.parentid):
            G.add_node(e.parentid, topic=str(e.parentid), parentid=None, expanded="false", depth=0, importance=0)
        if not G.has_node(e.childid):
            G.add_node(e.childid, topic=str(e.childid), parentid=e.parentid, expanded="false", depth=0, importance=0)
        G.add_edge(e.parentid, e.childid, relation=e.relation, order=int(getattr(e, "order", 0) or 0))
    persist_graph(G, csv_path)


def index_by_id(nodes: List[Node]) -> Dict[str, Node]:
    return {n.id: n for n in nodes}


def index_by_topic_ci(nodes: List[Node]) -> Dict[str, Node]:
    idx: Dict[str, Node] = {}
    for n in nodes:
        key = n.topic.strip().lower()
        if key and key not in idx:
            idx[key] = n
    return idx


def get_hierarchy(node: Node, nodes_by_id: Dict[str, Node]) -> List[str]:
    hierarchy = []
    current = node
    while current:
        hierarchy.append(current.topic)
        if current.parentid is None:
            break
        current = nodes_by_id.get(current.parentid)
    return list(reversed(hierarchy))


def first_unexpanded(nodes: List[Node]) -> Optional[Node]:
    for n in nodes:
        if normalize_expanded(n.expanded) == "false":
            return n
    return None


def build_topic_index(G: nx.DiGraph) -> Dict[str, str]:
    idx: Dict[str, str] = {}
    for nid, data in G.nodes(data=True):
        key = str(data.get("topic", "")).strip().lower()
        if key and key not in idx:
            idx[key] = str(nid)
    return idx


def ensure_root(G: nx.DiGraph) -> None:
    if G.number_of_nodes() == 0:
        G.add_node("root", topic=ROOT_TOPIC, parentid=None, expanded="false", depth=0, importance=10)


def normalize_node(obj: Any, parentid: Optional[str], parentdepth: int) -> Optional[Node]:
    if obj is None:
        return None
    if isinstance(obj, Node):
        d = getattr(obj, "depth", parentdepth)
        imp = int(getattr(obj, "importance", 0) or 0)
        return Node(
            id=str(obj.id),
            topic=str(obj.topic),
            parentid=obj.parentid if obj.parentid is not None else parentid,
            expanded=normalize_expanded(getattr(obj, "expanded", "false")),
            depth=int(d),
            importance=imp,
        )
    if isinstance(obj, dict):
        nid = str(obj.get("id", "")).strip()
        topic = str(obj.get("topic", "")).strip()
        pid = obj.get("parentid", parentid)
        pid = None if pid in (None, "", "None") else str(pid)
        exp = normalize_expanded(obj.get("expanded", "false"))
        dval = obj.get("depth", parentdepth + (0 if pid is None else 1))
        try:
            d = int(dval)
        except Exception:
            d = parentdepth + (0 if pid is None else 1)
        imp_raw = obj.get("importance", 0)
        try:
            imp = int(imp_raw)
        except Exception:
            imp = 0
        return Node(id=nid, topic=topic, parentid=pid, expanded=exp, depth=int(d), importance=imp)
    if isinstance(obj, (tuple, list)) and len(obj) >= 2:
        nid = str(obj[0])
        topic = str(obj[1])
        imp = 0
        if len(obj) >= 3:
            try:
                imp = int(obj[2])
            except Exception:
                imp = 0
        return Node(id=nid, topic=topic, parentid=parentid, expanded="false", depth=parentdepth + 1, importance=imp)
    return None


def add_children(nodes: List[Node], parent: Node, children: Iterable[Any]) -> int:
    by_id = index_by_id(nodes)
    by_topic = index_by_topic_ci(nodes)
    added = 0
    for child in children or []:
        normalized = normalize_node(child, parentid=parent.id, parentdepth=parent.depth)
        if not normalized:
            continue
        key = normalized.topic.strip().lower()
        existing = by_topic.get(key)
        if existing:
            # Node with same topic exists, only ensure parentid on first link if child has no primary parent
            # Do not create duplicate node
            pass
        else:
            nodes.append(normalized)
            by_id[normalized.id] = normalized
            by_topic[key] = normalized
            added += 1
    parent.expanded = "true"
    return added


def generate_tree_live(socketio: SocketIO, csv_path: str, max_nodes: int = 1000) -> None:
    G = load_graph(csv_path)
    ensure_root(G)
    topic_idx = build_topic_index(G)
    socketio.emit('existing_nodes', [n.__dict__ for n in nodes_from_graph(G)])
    existing_edges = [
        {"parentid": str(u), "childid": str(v), "relation": d.get("relation", "is_a"), "order": int(d.get("order", 0) or 0)}
        for u, v, d in G.edges(data=True)
    ]
    if existing_edges:
        socketio.emit('existing_edges', existing_edges)

    total_added = 0
    while total_added < max_nodes:
        if G.number_of_nodes() >= max_nodes:
            break
        current_id = None
        for nid, data in G.nodes(data=True):
            if normalize_expanded(data.get("expanded", "false")) == "false":
                current_id = str(nid)
                break
        if current_id is None:
            break

        current = Node(
            id=current_id,
            topic=str(G.nodes[current_id].get("topic", "")),
            parentid=G.nodes[current_id].get("parentid"),
            expanded=normalize_expanded(G.nodes[current_id].get("expanded", "false")),
            depth=int(G.nodes[current_id].get("depth", 0) or 0),
            importance=int(G.nodes[current_id].get("importance", 0) or 0),
        )

        socketio.emit('update_node', current.__dict__)
        socketio.sleep(0.1)

        if int(current.importance or 0) < 6:
            G.nodes[current.id]["expanded"] = "skipped"
            children = None
        else:
            try:
                nodes_by_id = {str(nid): Node(id=str(nid), topic=str(d.get("topic", "")), parentid=d.get("parentid"), expanded=normalize_expanded(d.get("expanded", "false")), depth=int(d.get("depth", 0) or 0), importance=int(d.get("importance", 0) or 0)) for nid, d in G.nodes(data=True)}
                hierarchy = get_hierarchy(current, nodes_by_id)
                children = expand(current.topic, hierarchy)
            except Exception as e:
                print(f"Failed to expand {current.topic}: {e}")
                children = None

        new_nodes: List[Node] = []
        new_edges: List[Edge] = []
        if isinstance(children, list) and len(children) > 0:
            reached_limit = False
            for child in children:
                normalized = normalize_node(child, parentid=current.id, parentdepth=current.depth)
                if not normalized:
                    continue
                key = normalized.topic.strip().lower()
                existing_id = topic_idx.get(key)
                if existing_id:
                    if not G.has_edge(current.id, existing_id):
                        G.add_edge(current.id, existing_id, relation="is_a", order=0)
                        new_edges.append(Edge(parentid=current.id, childid=existing_id))
                else:
                    if G.number_of_nodes() >= max_nodes:
                        reached_limit = True
                        break
                    G.add_node(
                        normalized.id,
                        topic=normalized.topic,
                        parentid=current.id,
                        expanded="false",
                        depth=current.depth + 1,
                        importance=int(getattr(normalized, "importance", 0) or 0),
                    )
                    topic_idx[key] = normalized.id
                    new_nodes.append(Node(id=normalized.id, topic=normalized.topic, parentid=current.id, expanded="false", depth=current.depth + 1, importance=int(getattr(normalized, "importance", 0) or 0)))
                    G.add_edge(current.id, normalized.id, relation="is_a", order=0)
                    new_edges.append(Edge(parentid=current.id, childid=normalized.id))

            G.nodes[current.id]["expanded"] = "true"
            total_added += len(new_nodes)
            persist_graph(G, csv_path)
            if reached_limit:
                break

            for n in new_nodes:
                socketio.emit('new_node', n.__dict__)
                socketio.sleep(0.05)
            for e in new_edges:
                socketio.emit('new_edge', {"from": e.parentid, "to": e.childid})
                socketio.sleep(0.02)
            socketio.emit('batch_ready', {"parentid": current.id, "children": [n.id for n in new_nodes]})
        elif isinstance(children, list) and len(children) == 0:
            G.nodes[current.id]["expanded"] = "skipped"
            persist_graph(G, csv_path)
            socketio.emit('batch_ready', {"parentid": current.id, "children": []})
        else:
            if normalize_expanded(G.nodes[current.id].get("expanded", "false")) == "skipped":
                G.nodes[current.id]["expanded"] = "skipped"
            else:
                G.nodes[current.id]["expanded"] = "true"
            persist_graph(G, csv_path)
            socketio.emit('batch_ready', {"parentid": current.id, "children": []})

def update_csv_tree(csv_path: str, max_nodes: int = 1000) -> List[Node]:
    G = load_graph(csv_path)
    ensure_root(G)
    topic_idx = build_topic_index(G)

    total_added = 0
    while total_added < max_nodes:
        if G.number_of_nodes() >= max_nodes:
            break
        current_id = None
        for nid, data in G.nodes(data=True):
            if normalize_expanded(data.get("expanded", "false")) == "false":
                current_id = str(nid)
                break
        if current_id is None:
            break

        current_topic = str(G.nodes[current_id].get("topic", ""))
        current_depth = int(G.nodes[current_id].get("depth", 0) or 0)
        current_importance = int(G.nodes[current_id].get("importance", 0) or 0)

        if int(current_importance or 0) < 6:
            G.nodes[current_id]["expanded"] = "skipped"
            persist_graph(G, csv_path)
            continue
        try:
            nodes_by_id = {str(nid): Node(id=str(nid), topic=str(d.get("topic", "")), parentid=d.get("parentid"), expanded=normalize_expanded(d.get("expanded", "false")), depth=int(d.get("depth", 0) or 0), importance=int(d.get("importance", 0) or 0)) for nid, d in G.nodes(data=True)}
            current_node = nodes_by_id[current_id]
            hierarchy = get_hierarchy(current_node, nodes_by_id)
            children = expand(current_topic, hierarchy)
        except Exception as e:
            print(f"Failed to expand {current_topic}: {e}")
            children = None

        new_nodes_count = 0
        if isinstance(children, list) and len(children) > 0:
            reached_limit = False
            for child in children:
                normalized = normalize_node(child, parentid=current_id, parentdepth=current_depth)
                if not normalized:
                    continue
                key = normalized.topic.strip().lower()
                existing_id = topic_idx.get(key)
                if existing_id:
                    if not G.has_edge(current_id, existing_id):
                        G.add_edge(current_id, existing_id, relation="is_a", order=0)
                else:
                    if G.number_of_nodes() >= max_nodes:
                        reached_limit = True
                        break
                    G.add_node(
                        normalized.id,
                        topic=normalized.topic,
                        parentid=current_id,
                        expanded="false",
                        depth=current_depth + 1,
                        importance=int(getattr(normalized, "importance", 0) or 0),
                    )
                    topic_idx[key] = normalized.id
                    G.add_edge(current_id, normalized.id, relation="is_a", order=0)
                    new_nodes_count += 1

            G.nodes[current_id]["expanded"] = "true"
            total_added += new_nodes_count
            persist_graph(G, csv_path)
            if reached_limit:
                break
        elif isinstance(children, list) and len(children) == 0:
            G.nodes[current_id]["expanded"] = "skipped"
            persist_graph(G, csv_path)
        else:
            if normalize_expanded(G.nodes[current_id].get("expanded", "false")) == "skipped":
                G.nodes[current_id]["expanded"] = "skipped"
            else:
                G.nodes[current_id]["expanded"] = "true"
            persist_graph(G, csv_path)

    return nodes_from_graph(G)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "graph", "tree.csv")
MAX_NODES = 30000


def main() -> None:
    nodes = update_csv_tree(CSV_PATH, max_nodes=MAX_NODES)
    print(f"Wrote {len(nodes)} nodes to {CSV_PATH}")


if __name__ == "__main__":
    main()