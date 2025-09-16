import csv
import json
import os
import secrets
import tempfile
from dataset.dialogue_engine import generate_dialogue


def generate_text(topic: str) -> str:
    return ""


def load_order_ids(order_path: str) -> list[str]:
    with open(order_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    ids = data.get("ids", [])
    return [x for x in ids if isinstance(x, str) and x]


def load_topic_lookup(csv_path: str) -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rid = row.get("id")
            topic = row.get("topic")
            path = row.get("path")
            if not isinstance(rid, str) or not rid or not isinstance(topic, str) or not topic:
                continue
            try:
                d = int(row.get("depth", "0"))
            except ValueError:
                continue
            if d >= 4:
                lookup[rid] = {"topic": topic, "path": path or ""}
    return lookup


def load_cursor(state_path: str) -> int:
    if not os.path.exists(state_path):
        return 0
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        c = data.get("cursor", 0)
        return int(c) if isinstance(c, int) else 0
    except Exception:
        return 0


def save_cursor(state_path: str, cursor: int) -> None:
    state_dir = os.path.dirname(state_path)
    os.makedirs(state_dir, exist_ok=True)
    payload = {"cursor": cursor}
    with tempfile.NamedTemporaryFile("w", delete=False, dir=state_dir, prefix=".tmp_state_", suffix=".json", encoding="utf-8") as tmp:
        json.dump(payload, tmp, ensure_ascii=False)
        tmp_path = tmp.name
    os.replace(tmp_path, state_path)


def ensure_order(csv_path: str, order_path: str) -> None:
    if os.path.exists(order_path):
        return
    try:
        from dataset.make_topics_order import main as make_order_main

        make_order_main(csv_path=csv_path, order_path=order_path)
    except Exception:
        raise FileNotFoundError(
            f"Missing order file at {order_path} and failed to generate it."
        )


def build_dataset(
    csv_path: str = "data/topics.csv",
    order_path: str = "data/topics.order.json",
    output_path: str = "data/dataset.jsonl",
    state_path: str = "data/dataset.state.json",
) -> None:
    ensure_order(csv_path, order_path)
    ids = load_order_ids(order_path)
    topic_lookup = load_topic_lookup(csv_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cursor = load_cursor(state_path)
    total = len(ids)
    if cursor >= total:
        return
    with open(output_path, "a", encoding="utf-8") as out_file:
        for i in range(cursor, total):
            rid = ids[i]
            rec = topic_lookup.get(rid)
            if not rec:
                save_cursor(state_path, i + 1)
                continue
            topic_value = rec["topic"]
            path_value = rec.get("path", "")
            data_id = secrets.token_hex(4)
            gen = generate_dialogue(topic_value, path_value)
            text_value = gen if isinstance(gen, str) and gen is not None else ""
            obj = {"id": data_id, "topic": topic_value, "text": text_value}
            out_file.write(json.dumps(obj, ensure_ascii=False) + "\n")
            out_file.flush()
            save_cursor(state_path, i + 1)


if __name__ == "__main__":
    build_dataset()