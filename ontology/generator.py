from typing import Optional, Iterable, Any, Type
import os
from pathlib import Path
import uuid
import random
from openai import OpenAI
from pydantic import BaseModel, Field
import instructor
from prompts import build_expand_prompt
try:
    from dotenv import load_dotenv as _load_dotenv
except Exception:
    _load_dotenv = None

def _find_env_path() -> Optional[Path]:
    start = Path(__file__).resolve().parent
    for parent in [start] + list(start.parents):
        envp = parent / ".env"
        if envp.exists():
            return envp
    return None

def openai_client() -> OpenAI:
    env_path = _find_env_path()
    if _load_dotenv is not None and env_path is not None:
        _load_dotenv(dotenv_path=env_path, override=False)
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

def candidate_models() -> list[str]:
    s = os.getenv("MODEL_LIST", "").strip()
    if s:
        return [m.strip() for m in s.split(",") if m.strip()]
    single = os.getenv("OPENAI_MODEL", "").strip()
    if single:
        return [single]
    return [
        "anthropic/claude-sonnet-4",
        "openai/gpt-5",
        "qwen/qwen3-max"
    ]

def session() -> tuple[OpenAI, str]:
    global _CLIENT, _MODEL
    if _CLIENT is None:
        _CLIENT = openai_client()
    pool = candidate_models()
    _MODEL = random.choice(pool) if pool else "openai/gpt-4o-mini"
    return _CLIENT, _MODEL

class RootTopic(BaseModel):
    topic: str = Field(min_length=1)

class Subtopic(BaseModel):
    topic: str = Field(min_length=1)
    importance: int = Field(ge=0, le=10)

class Subtopics(BaseModel):
    subtopics: list[Subtopic] = Field(default_factory=list)

def chat_request(client: OpenAI, model: str, prompt: str, response_model: Type[BaseModel]) -> Any:
    msgs = [{"role": "user", "content": prompt}]
    return client.chat.completions.create(
        model=model,
        messages=msgs,
        reasoning_effort='minimal',
        response_model=response_model,
        max_tokens=512
    )

def expand(topic: str, hierarchy: list[str]) -> Optional[Iterable[Any]]:
    client, model = session()
    path = " > ".join(hierarchy)
    prompt = build_expand_prompt(topic, path)
    resp = chat_request(client, model, prompt, response_model=Subtopics)
    if not resp.subtopics:
        return []
    result: list[tuple[str, str, int]] = []
    for s in resp.subtopics:
        topic_name = str(getattr(s, "topic", "")).strip()
        try:
            imp_raw = int(getattr(s, "importance", 0) or 0)
        except Exception:
            imp_raw = 0
        imp = max(0, min(10, imp_raw))
        if not topic_name:
            continue
        result.append((uuid.uuid4().hex[:8], topic_name, imp))
    return result