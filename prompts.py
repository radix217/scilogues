def build_expand_prompt(topic: str, path: str) -> str:
    return (
        f"""
You are expanding a tree of all scientific knowledge.
Starting with root 'Knowledge' to branch out and include everything. Only include what is scientifically recognized.

The current path is '{path}'. The current topic is '{topic}'.

Instructions:
1. Return only immediate subcategories of '{topic}' that are mutually exclusive, ontologically real, and scientifically recognized.
2. Exclude non-scientific concepts, cultural constructs, or vague ideas.
3. Keep granularity consistent: each child is exactly one level more specific than '{topic}'.
4. Do not jump multiple levels down the hierarchy.
5. Avoid pseudoscience, overlapping categories, and duplicate concepts.
6. Exclude non-technical, non-scientific topics (e.g. history, sociology, humanities).
7. Nest subcategories under the most fundamental parent possible.
8. For each subtopic, assign an integer importance score from 0 to 10 representing how important it is in this batch, whether to branch ahead or not.
   Score meanings:
   - 0–2: Strongly recommend NOT branching
   - 3–4: Recommend NOT branching
   - 5: Neutral / No strong recommendation
   - 6–7: Recommend branching
   - 8–10: Strongly recommend branching
   Only subtopics with importance >= 6 will be expanded downstream; score accordingly.
9. Return strictly as JSON with this exact shape:
   {{
     "subtopics": [
       {{ "topic": "...", "importance": 0 }},
       ...
     ]
   }}

"""
    )
