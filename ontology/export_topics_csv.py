import argparse
import csv
import os
import pickle
from typing import Dict, List

import networkx as nx


def load_graph(pkl_path: str) -> nx.DiGraph:
    with open(pkl_path, "rb") as f:
        G = pickle.load(f)
    if not isinstance(G, nx.DiGraph):
        G = nx.DiGraph(G)
    return G


def build_parent_index(G: nx.DiGraph) -> Dict[str, str]:
    idx: Dict[str, str] = {}
    for nid, data in G.nodes(data=True):
        pid = data.get("parentid")
        idx[str(nid)] = None if pid in (None, "", "None") else str(pid)
    return idx


def build_topic_index(G: nx.DiGraph) -> Dict[str, str]:
    idx: Dict[str, str] = {}
    for nid, data in G.nodes(data=True):
        idx[str(nid)] = str(data.get("topic", ""))
    return idx


def path_from_root(node_id: str, parent: Dict[str, str], topic: Dict[str, str]) -> List[str]:
    chain: List[str] = []
    cur = node_id
    visited = set()
    while cur is not None and cur not in visited:
        visited.add(cur)
        chain.append(topic.get(cur, ""))
        cur = parent.get(cur)
    chain.reverse()
    return chain


def export_topics_csv(pkl_path: str, csv_path: str) -> None:
    G = load_graph(pkl_path)
    parent = build_parent_index(G)
    topic = build_topic_index(G)
    root_topic = ""
    for nid, data in G.nodes(data=True):
        if data.get("parentid") in (None, "", "None"):
            root_topic = str(data.get("topic", ""))
            break
    rows = []
    for nid, data in G.nodes(data=True):
        sid = str(nid)
        topics = path_from_root(sid, parent, topic)
        if topics and topics[0] == root_topic:
            topics = topics[1:]
        depth = int(data.get("depth", max(0, len(topics) - 1)) or 0)
        rows.append({
            "id": sid,
            "topic": topic.get(sid, ""),
            "path": " > ".join(topics),
            "depth": depth,
        })
    os.makedirs(os.path.dirname(os.path.abspath(csv_path)), exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "topic", "path", "depth"])
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    default_pkl = os.path.join(root_dir, "data", "ontology", "tree.pkl")
    default_out = os.path.join(root_dir, "data", "topics.csv")
    parser.add_argument("--pkl", default=default_pkl)
    parser.add_argument("--out", default=default_out)
    args = parser.parse_args()
    export_topics_csv(args.pkl, args.out)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
