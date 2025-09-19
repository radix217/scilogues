---
annotations_creators:
  - machine-generated
language:
  - en
license: other
multilinguality:
  - monolingual
task_categories:
  - text-generation
pretty_name: Scilogues Synthetic Dialogue Dataset
size_categories:
  - 1K<n<10K
source_datasets:
  - original
paperswithcode_id: null
configs: []
---

# Dataset Card for Scilogues Synthetic Dialogue Dataset

## Dataset Summary
Synthetic multi-speaker reasoning-rich dialogues based on scientific topics. This (first) version of the dataset has ~2M tokens of conversation (~5.5k rows) based on a balanced range of topics derived from a scientific ontology. Each record pairs a `topic` string with a free-form dialogue `text`. Texts are produced with an LLM using varied constraints to encourage stylistic diversity, and search for grounding and accuracy.

## Supported Tasks
- text-generation

## Languages
- English (`en`)

## Dataset Structure

### Data Instances
Each line in `data/dataset.jsonl` is a JSON object:
```json
{
  "id": "9f3a2b1c",
  "topic": "Quantum entanglement experiments",
  "text": "Alice: ...\nBob: ...\n..."
}
```

### Data Fields
- `id`: hex string, locally unique per example
- `topic`: string, leaf-level topic sourced from `data/topics.csv`
- `text`: string, generated multi-turn dialogue content

### Data Splits
The dataset is provided as a single JSONL file without predefined splits. Create splits deterministically if needed, for example by hashing `id`.


## Example Usage
```python
from datasets import load_dataset

data = load_dataset(
    "json",
    data_files={"train": "data/dataset.jsonl"},
    split="train",
)
print(data[0])
```