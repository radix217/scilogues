from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Iterable, Dict, Any, Tuple
import csv
import os
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


def read_nodes(csv_path: str) -> List[Node]:
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        return []
    nodes: List[Node] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            nodes.append(
                Node(
                    id=str(row.get("id", "")).strip(),
                    topic=str(row.get("topic", "")).strip(),
                    parentid=(p if (p := str(row.get("parentid", "")).strip()) != "" else None),
                    expanded=normalize_expanded(row.get("expanded", "false")),
                    depth=int(str(row.get("depth", "0")).strip() or 0),
                    importance=int(str(row.get("importance", "0")).strip() or 0),
                )
            )
    return nodes


def write_nodes(csv_path: str, nodes: List[Node]) -> None:
    fieldnames = ["id", "topic", "parentid", "expanded", "depth", "importance"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for n in nodes:
            writer.writerow(
                {
                    "id": n.id,
                    "topic": n.topic,
                    "parentid": "" if n.parentid is None else n.parentid,
                    "expanded": normalize_expanded(getattr(n, "expanded", "false")),
                    "depth": int(getattr(n, "depth", 0) or 0),
                    "importance": int(getattr(n, "importance", 0) or 0),
                }
            )


def read_edges(csv_path: str) -> List[Edge]:
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        return []
    edges: List[Edge] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = str(row.get("parentid", "")).strip()
            cid = str(row.get("childid", "")).strip()
            rel = str(row.get("relation", "is_a")).strip() or "is_a"
            try:
                order = int(str(row.get("order", "0")).strip() or 0)
            except Exception:
                order = 0
            if pid and cid:
                edges.append(Edge(parentid=pid, childid=cid, relation=rel, order=order))
    return edges


def write_edges(csv_path: str, edges: List[Edge]) -> None:
    fieldnames = ["parentid", "childid", "relation", "order"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for e in edges:
            writer.writerow(
                {
                    "parentid": e.parentid,
                    "childid": e.childid,
                    "relation": e.relation,
                    "order": int(getattr(e, "order", 0) or 0),
                }
            )


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
        imp = obj.get("importance", 0)
        try:
            impi = int(imp)
        except Exception:
            impi = 0
        return Node(id=nid, topic=topic, parentid=pid, expanded=exp, depth=int(d), importance=impi)
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
    nodes_csv = csv_path
    edges_csv = os.path.splitext(csv_path)[0] + "_edges.csv"

    nodes = read_nodes(nodes_csv)
    edges = read_edges(edges_csv)

    nodes_by_id = index_by_id(nodes)
    topic_idx = index_by_topic_ci(nodes)
    edge_set = {(e.parentid, e.childid) for e in edges}

    socketio.emit('existing_nodes', [n.__dict__ for n in nodes])
    if edges:
        socketio.emit('existing_edges', [e.__dict__ for e in edges])

    if not nodes:
        root_node = Node(id="root", topic=ROOT_TOPIC, parentid=None, expanded="false", depth=0, importance=10)
        nodes.append(root_node)
        nodes_by_id[root_node.id] = root_node
        topic_idx[root_node.topic.strip().lower()] = root_node
        write_nodes(nodes_csv, nodes)
        socketio.emit('new_node', root_node.__dict__)

    total_added = 0
    while total_added < max_nodes:
        current = first_unexpanded(nodes)
        if current is None:
            break

        socketio.emit('update_node', current.__dict__)
        socketio.sleep(0.1)

        if int(getattr(current, "importance", 0) or 0) < 6:
            current.expanded = "skipped"
            children = None
        else:
            try:
                hierarchy = get_hierarchy(current, nodes_by_id)
                children = expand(current.topic, hierarchy)
            except Exception as e:
                print(f"Failed to expand {current.topic}: {e}")
                children = None

        new_nodes: List[Node] = []
        new_edges: List[Edge] = []
        if children:
            for child in children:
                normalized = normalize_node(child, parentid=current.id, parentdepth=current.depth)
                if not normalized:
                    continue
                key = normalized.topic.strip().lower()
                existing = topic_idx.get(key)
                if existing:
                    if (current.id, existing.id) not in edge_set:
                        e = Edge(parentid=current.id, childid=existing.id)
                        edges.append(e)
                        edge_set.add((current.id, existing.id))
                        new_edges.append(e)
                else:
                    n = Node(
                        id=normalized.id,
                        topic=normalized.topic,
                        parentid=current.id,
                        expanded="false",
                        depth=current.depth + 1,
                        importance=int(getattr(normalized, "importance", 0) or 0),
                    )
                    nodes.append(n)
                    nodes_by_id[n.id] = n
                    topic_idx[key] = n
                    new_nodes.append(n)
                    e = Edge(parentid=current.id, childid=n.id)
                    edges.append(e)
                    edge_set.add((current.id, n.id))
                    new_edges.append(e)

            current.expanded = "true"
            total_added += len(new_nodes)

            # Emit new nodes and edges
            for n in new_nodes:
                socketio.emit('new_node', n.__dict__)
                socketio.sleep(0.05)
            for e in new_edges:
                socketio.emit('new_edge', {"from": e.parentid, "to": e.childid})
                socketio.sleep(0.02)
            socketio.emit('batch_ready', {"parentid": current.id, "children": [n.id for n in new_nodes]})
        else:
            if normalize_expanded(current.expanded) == "skipped":
                current.expanded = "skipped"
            else:
                current.expanded = "true"
            socketio.emit('batch_ready', {"parentid": current.id, "children": []})

        write_nodes(nodes_csv, nodes)
        write_edges(edges_csv, edges)

    write_nodes(nodes_csv, nodes)
    write_edges(edges_csv, edges)

def update_csv_tree(csv_path: str, max_nodes: int = 1000) -> List[Node]:
    nodes = read_nodes(csv_path)
    if not nodes:
        nodes.append(Node(id="root", topic=ROOT_TOPIC, parentid=None, expanded="false", depth=0, importance=10))
        write_nodes(csv_path, nodes)
    total_added = 0
    nodes_by_id = index_by_id(nodes)
    while total_added < max_nodes:
        current = first_unexpanded(nodes)
        if current is None:
            break
        if int(getattr(current, "importance", 0) or 0) < 6:
            current.expanded = "skipped"
            children = None
        else:
            try:
                hierarchy = get_hierarchy(current, nodes_by_id)
                children = expand(current.topic, hierarchy)
            except Exception as e:
                print(f"Failed to expand {current.topic}: {e}")
                children = None
        before = len(nodes)
        if children:
            added_count = add_children(nodes, current, children)
            total_added += added_count
            if added_count > 0:
                nodes_by_id = index_by_id(nodes)
        else:
            if normalize_expanded(current.expanded) == "skipped":
                current.expanded = "skipped"
            else:
                current.expanded = "true"
        if len(nodes) == before and normalize_expanded(current.expanded) != "false" and first_unexpanded(nodes) is None:
            break
        write_nodes(csv_path, nodes)
    write_nodes(csv_path, nodes)
    return nodes


CSV_PATH = "tree.csv"
MAX_NODES = 25000


def main() -> None:
    # This function is now intended for offline generation.
    # For the live web server, run app.py
    nodes = update_csv_tree(CSV_PATH, max_nodes=MAX_NODES)
    print(f"Wrote {len(nodes)} nodes to {CSV_PATH}")


if __name__ == "__main__":
    main()