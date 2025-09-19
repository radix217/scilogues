import csv
import json
import os
import secrets
import tempfile
import sys
import asyncio
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
    workers: int = 8,
    batch_size: int | None = None,
) -> None:
    ensure_order(csv_path, order_path)
    ids = load_order_ids(order_path)
    topic_lookup = load_topic_lookup(csv_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cursor = load_cursor(state_path)
    total = len(ids)
    if cursor >= total:
        return
    if batch_size is None:
        batch_size = max(1, workers * 2)

    async def process() -> None:
        nonlocal cursor
        try:
            with open(output_path, "a", encoding="utf-8") as out_file:
                i = cursor
                while i < total:
                    end = min(i + batch_size, total)
                    meta: list[tuple[int, str, dict[str, str] | None]] = []
                    tasks: list[asyncio.Task] = []
                    sem = asyncio.Semaphore(workers)

                    async def run_one(topic_value: str, path_value: str):
                        async with sem:
                            return await generate_dialogue(topic_value, path_value)

                    for j in range(i, end):
                        rid = ids[j]
                        rec = topic_lookup.get(rid)
                        if not rec:
                            meta.append((j, rid, None))
                            continue
                        meta.append((j, rid, rec))
                        topic_value = rec["topic"]
                        path_value = rec.get("path", "")
                        tasks.append(asyncio.create_task(run_one(topic_value, path_value)))

                    results = await asyncio.gather(*tasks, return_exceptions=True) if tasks else []

                    k = 0
                    for pos, rid, rec in meta:
                        if not rec:
                            continue
                        topic_value = rec["topic"]
                        try:
                            res = results[k]
                            k += 1
                        except IndexError:
                            print(
                                f"[generation_error] id={rid} topic={topic_value} type=IndexError message=results_alignment",
                                file=sys.stderr,
                                flush=True,
                            )
                            continue
                        if isinstance(res, Exception):
                            print(
                                f"[generation_error] id={rid} topic={topic_value} type={type(res).__name__} message={res}",
                                file=sys.stderr,
                                flush=True,
                            )
                            continue
                        if not isinstance(res, str) or res is None:
                            print(
                                f"[invalid_output] id={rid} topic={topic_value} reason=non_string_or_none",
                                file=sys.stderr,
                                flush=True,
                            )
                            continue
                        words = [w for w in res.strip().split() if w]
                        if len(words) < 50:
                            print(
                                f"[invalid_output] id={rid} topic={topic_value} reason=too_short word_count={len(words)}",
                                file=sys.stderr,
                                flush=True,
                            )
                            continue
                        data_id = secrets.token_hex(4)
                        obj = {"id": data_id, "topic": topic_value, "text": res}
                        out_file.write(json.dumps(obj, ensure_ascii=False) + "\n")
                        out_file.flush()

                    save_cursor(state_path, end)
                    i = end
        except KeyboardInterrupt:
            save_cursor(state_path, i if 'i' in locals() else cursor)
            raise

    asyncio.run(process())


if __name__ == "__main__":
    build_dataset()