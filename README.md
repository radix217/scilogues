Scilogues

Overview

Scilogues generates a hierarchical ontology of topics and uses it to synthesize multi‑speaker dialogues as a dataset. It includes:

- Ontology generation and persistence using `networkx` and LLMs
- CSV export of topics with hierarchical paths
- Async dialogue generation over topics into JSONL
- A simple Flask visualizer for the ontology graph

Project structure

- `ontology/` — Ontology generation, storage, and tools
  - `ontology/ontology_tree.py` — in‑memory graph + persistence (`data/ontology/tree.pkl`)
  - `ontology/generator.py` — LLM wrapper and model/session selection
  - `ontology/export_topics_csv.py` — export topics with paths to `data/topics.csv`
  - `ontology/visualizer/` — minimal Flask app to view the graph
- `dataset/` — Dataset builders over topics
  - `dataset/build_dataset.py` — async dialogue generation to `data/dataset.jsonl`
  - `dataset/dialogue_engine.py` — OpenAI client + prompting hooks
- `data/` — Artifacts: ontology pickle, topics CSV, order file, and generated dataset

Requirements

- Python 3.10+
- Install deps:

  ```bash
  pip install -r requirements.txt
  ```

Environment

Create a `.env` at the repository root:

```
OPENAI_API_KEY=...
# Optional
OPENAI_BASE_URL=
OPENROUTER_REFERER=http://localhost:5000
OPENROUTER_TITLE=scilogues
MODEL_LIST=  # comma‑separated overrides for ontology expansion
OPENAI_MODEL=  # single‑model override for ontology expansion
```

Key workflows

- Generate/extend ontology graph pickle

  ```bash
  python -m ontology.ontology_tree
  ```

  Writes/updates `data/ontology/tree.pkl` and keeps a working CSV path handle internally.

- Export topics CSV with hierarchical paths

  ```bash
  python -m ontology.export_topics_csv --pkl data/ontology/tree.pkl --out data/topics.csv
  ```

- Build dialogue dataset from topics (JSONL)

  ```bash
  python -m dataset.build_dataset
  ```

  Inputs `data/topics.csv` and `data/topics.order.json`. Appends items to `data/dataset.jsonl`. Resumable via `data/dataset.state.json`.

- Run ontology visualizer (Flask)

  ```bash
  python -m ontology.visualizer.app
  ```

  Note: the visualizer reads via `ontology_tree.read_nodes/read_edges` from paths inside `ontology/visualizer/app.py`. Ensure paths point to your graph data; default project data lives under `data/ontology/`.

Quickstart

```bash
pip install -r requirements.txt
cp .env.example .env  # or create .env and set OPENAI_API_KEY
python -m ontology.ontology_tree
python -m ontology.export_topics_csv
python -m dataset.build_dataset
python -m ontology.visualizer.app
```

Notes

- Dialogue generation uses the `perplexity/sonar-reasoning` chat model by default in `dataset/dialogue_engine.py`. Configure via environment if needed.
- Ontology expansion randomly selects from `MODEL_LIST` or `OPENAI_MODEL` in `ontology/generator.py`.