from typing import Optional, Iterable, Any, Type
import os
import json
from pathlib import Path
import uuid
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError
import instructor


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if not line or line.strip().startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def openai_client() -> OpenAI:
    load_env_file(Path(__file__).resolve().parent / ".env")
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required")
    kwargs: dict[str, Any] = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
        if "openrouter.ai" in base_url:
            referer = os.getenv("OPENROUTER_REFERER", "http://localhost:5000").strip()
            title = os.getenv("OPENROUTER_TITLE", "scilogues").strip()
            kwargs["default_headers"] = {"HTTP-Referer": referer, "X-Title": title}
    return instructor.patch(OpenAI(**kwargs))

_CLIENT: Optional[OpenAI] = None
_MODEL: Optional[str] = None

def session() -> tuple[OpenAI, str]:
    global _CLIENT, _MODEL
    if _CLIENT is None:
        _CLIENT = openai_client()
    if _MODEL is None:
        model = 'openai/gpt-5-mini'
        base_url = os.getenv("OPENAI_BASE_URL", "").strip()
        if base_url and "openrouter.ai" in base_url and "/" not in model:
            model = f"{model}"
        _MODEL = model
    return _CLIENT, _MODEL

class RootTopic(BaseModel):
    topic: str = Field(min_length=1)






class Subtopics(BaseModel):
    subtopics: list[str] = Field(default_factory=list)






def chat_request(client: OpenAI, model: str, prompt: str, response_model: Type[BaseModel]) -> Any:
    msgs = [{"role": "user", "content": prompt}]
    return client.chat.completions.create(
        model=model,
        messages=msgs,
        response_model=response_model,
    )


def createroot() -> Any:
    client, model = session()
    prompt = """You are constructing a hierarchical ontology of scientifically rigorous knowledge. 
The ontology must capture the structure of reality itself: the objects, phenomena, and abstract structures that science recognizes. 
We are starting with the root. 

Rules:
- The root must be the single most general concept that encompasses all scientifically rigorous entities.
- Do not return a scientific discipline (like physics or biology). 
- Return only the node label as JSON: { "topic": "..." }."""
    resp = chat_request(client, model, prompt, response_model=RootTopic)
    return {"id": "root", "topic": resp.topic, "parentid": None, "expanded": False}


def expand(topic: str, hierarchy: list[str]) -> Optional[Iterable[Any]]:
    client, model = session()
    path = " > ".join(hierarchy)
    prompt = f"""You are expanding an ontology tree of reality, built only from scientifically rigorous categories. 
The current path is '{path}'. The current topic is '{topic}'.

Rules:
- Return only immediate scientifically rigorous subcategories of '{topic}'. 
- Subtopics must represent "things that exist" (objects, phenomena, structures), not the disciplines that study them. 
- Keep granularity consistent: each child must be one clear level of specialization under its parent. 
- Do not include pseudoscience, cultural constructs, or vague/overlapping terms. 
- If a concept could fit under multiple parents, place it under the most fundamental/central one. 
- Avoid duplicates: a concept should appear only once in the tree. 

Return strictly as JSON: {{ "subtopics": [ ... ] }}"""
    resp = chat_request(client, model, prompt, response_model=Subtopics)
    if not resp.subtopics:
        return None
    return [(uuid.uuid4().hex[:8], s) for s in resp.subtopics]