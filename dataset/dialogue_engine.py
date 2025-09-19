import os
from random import choice
from functools import lru_cache
from openai import AsyncOpenAI
from dotenv import load_dotenv
from .population_builder import build_population
from .prompts import build_messages


root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
dotenv_path = os.path.join(root_dir, ".env")
load_dotenv(dotenv_path=dotenv_path, override=False)


@lru_cache(maxsize=1)
def get_async_client() -> AsyncOpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")
    return AsyncOpenAI(api_key=api_key, base_url=base_url) if base_url else AsyncOpenAI(api_key=api_key)


async def generate_dialogue(topic: str, path: str):
    sizes = [100, 200, 300, 400, 500]
    max_words = choice(sizes)
    characters = build_population()
    label_layouts = ["inline", "script", "none"]
    label_contents = [
        "name_normal",
        "generic_tagged_letter",
        "generic_tagged_number",
        "generic_letter",
        "generic_number",
        "role",
    ]
    label_layout = choice(label_layouts)
    label_content = choice(label_contents)
    client = get_async_client()
    system_msg, user_msg = build_messages(
        topic=topic,
        topic_path=path or "N/A",
        characters=characters,
        max_words=max_words,
        label_layout=label_layout,
        label_content=label_content,
    )
    resp = await client.chat.completions.create(
        model="perplexity/sonar-reasoning",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.8,
        max_tokens=min(2000, max_words * 2),
        reasoning_effort='medium'
    )
    content = resp.choices[0].message.content.strip()
    return content
