import csv
import json
import os
import random
import secrets
from typing import List


def load_eligible_ids(csv_path: str, min_depth: int) -> List[str]:
    ids: List[str] = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                d = int(row.get("depth", "0"))
            except ValueError:
                continue
            if d >= min_depth:
                rid = row.get("id")
                if isinstance(rid, str) and rid:
                    ids.append(rid)
    return ids


essential_fields = ["seed", "min_depth", "ids"]


def shuffle_and_save(ids: List[str], output_path: str, seed_int: int, min_depth: int) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    rng = random.Random(seed_int)
    rng.shuffle(ids)
    data = {"seed": format(seed_int, "016x"), "min_depth": int(min_depth), "ids": ids}
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def main(
    csv_path: str = "data/topics.csv",
    order_path: str = "data/topics.order.json",
    min_depth: int = 4,
    seed: int | None = None,
) -> None:
    if os.path.exists(order_path):
        return
    ids = load_eligible_ids(csv_path, min_depth)
    seed_int = int(seed) if seed is not None else secrets.randbits(64)
    shuffle_and_save(ids, order_path, seed_int, min_depth)


if __name__ == "__main__":
    main()
