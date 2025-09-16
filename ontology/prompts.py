def build_expand_prompt(topic: str, path: str) -> str:
    return (
        f"""
You are generating a tree of all scientific knowledge. 
Starting with root 'Knowledge' to branch out and include everything.
Domains, Objects (abstract / physical), Phenomenons, etc.
Only include what is scientifically recognized.

The current path is '{path}'.The current topic is '{topic}'.

Instructions:
1. Return only immediate subcategories of '{topic}' that are mutually exclusive, ontologically real, and scientifically recognized.
2. Exclude non-scientific concepts, cultural constructs, or vague ideas.
3. Keep granularity consistent: each child is exactly one level more specific than '{topic}'.
4. Do not jump multiple levels down the hierarchy.
5. Avoid pseudoscience, overlapping categories, and duplicate concepts.
6. Exclude non-technical, non-scientific and less rigorous topics (e.g. history, sociology, humanities).
7. Nest subcategories under the most fundamental parent possible.
8. Sort subtopics from most rigorous/fundamental to less rigorous. Prefer formal, axiomatized, mathematically grounded fields first; then empirical core sciences; then applied/less formal areas.
9. For each subtopic, assign an integer importance score from 0 to 10 representing how central/fundamental it is at this level.
   Meanings:
   - 0–2: Peripheral; strongly recommend not branching now
   - 3–4: Low priority; recommend not branching now
   - 5: Neutral
   - 6–7: Worth branching
   - 8–10: High priority; strongly recommend branching
   Only subtopics with importance >= 6 will be expanded downstream.
10. Dont cram in too much in the topic title. keep it 3-4 words max. ideall 1-2.
10. Return strictly as JSON with this exact shape:
   {{
     "subtopics": [
       {{ "topic": "...", "importance": 0 }},
       ...
     ]
   }}

"""
    )
