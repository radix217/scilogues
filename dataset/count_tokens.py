import argparse
import gzip
import io
import json
import os
from typing import Iterable, Union


def open_text_file(path: str) -> io.TextIOBase:
    if path.endswith(".gz"):
        return io.TextIOWrapper(gzip.open(path, mode="rb"), encoding="utf-8")
    return open(path, mode="r", encoding="utf-8")


def iter_strings(value: Union[dict, list, str, int, float, bool, None]) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from iter_strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from iter_strings(v)


def get_tokenizer(model: str):
    try:
        import tiktoken
    except Exception:
        return None
    try:
        return tiktoken.encoding_for_model(model)
    except Exception:
        return tiktoken.get_encoding("cl100k_base")


def count_tokens_in_texts(texts: Iterable[str], tokenizer) -> int:
    if tokenizer is None:
        total = 0
        for t in texts:
            total += len(t.split())
        return total
    total = 0
    for t in texts:
        total += len(tokenizer.encode(t))
    return total


def count_dataset_tokens(path: str, model: str) -> tuple[int, int]:
    tokenizer = get_tokenizer(model)
    total_tokens = 0
    total_rows = 0
    with open_text_file(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            texts = list(iter_strings(obj))
            total_tokens += count_tokens_in_texts(texts, tokenizer)
            total_rows += 1
    return total_tokens, total_rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default=os.path.join("data", "dataset.jsonl"))
    parser.add_argument("--model", default="gpt-4o-mini")
    args = parser.parse_args()
    total_tokens, total_rows = count_dataset_tokens(args.path, args.model)
    avg = (total_tokens / total_rows) if total_rows else 0
    print(json.dumps({
        "path": args.path,
        "rows": total_rows,
        "total_tokens": total_tokens,
        "avg_tokens_per_row": avg,
        "tokenizer": "tiktoken" if get_tokenizer(args.model) else "whitespace"
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
