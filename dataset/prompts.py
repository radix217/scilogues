from typing import Tuple
from random import random


def build_messages(topic: str, topic_path: str, characters: str, max_words: int, label_layout: str, label_content: str) -> Tuple[str, str]:
    char_lines = [ln for ln in characters.splitlines() if ln.strip()]
    format_block = _compose_format_rules(label_layout, label_content, len(char_lines))
    system_msg = f"""
You draft realistic and meaningful multiturn dialogues on given topic, with implicit reasoning chain unfolding in the dialogue.
Use all provided characters. Keep it coherent and self-contained. Output only the dialogue, strictly following the requested format and length.
Actively deep research the given topic on web and find relevant sources, Q/A, forum discussions, etc.
Find instances of problem solving, reasoning, questioning, etc. in the given topic, to base the conversation on. Such that training models on it will induce reasoning abilities as well as conversation abilities.
Avoid small talk and generic filler.
Never mention or cite any sources you consulted, and never state that you researched or searched; do not name websites, papers, forums, threads, or say you 'found' something online. (no URLs, no footnotes, and no mentions of sources or research)
Use brief inline LaTeX ($...$) or inline code only when the topic genuinely requires it; otherwise avoid it. Do not use multi-line code blocks or display math; keep each line a single dialogue line.
Treat all characters as equally intellectual, no condescension or caricature. Ensure each character contributes with arguments, collaborations, ideas, or questions of similar depth.
Characters should probe, challenge, and verify each other's claims, propose small thought experiments or examples, and elucidate their reasoning, and update positions when counter-evidence arises.

Format:
{format_block}

Additional Notes:
- Do not use the phrases 'Wait...', 'So you're saying...', 'I'm still <verb>...'
- Do not start with this cliche 'one person is having a problem or is confused'. you did that a lot before. don't use it now.
- Do not use university related premises, labs, clubs, coffee shops as settings. that is overdone for now.
"""
    show_setting = random() < 0.3
    setting_directive = (
        "Begin with one ultra-brief setting line (<=12 words), then the dialogue."
        if show_setting
        else "Do not include any setting line; start directly with the dialogue."
    )

    user_msg = f"""
Topic: {topic}
Context of the topic: {topic_path or 'N/A'}
Characters :
{characters}

Maximum length: {max_words} words.
Use the Topic to guide specificity. Integrate concrete factual particulars and reasoning patterns you found in sources, without citing or naming sources.
Pick a fitting setting suitable for the character demographic, including place, time period, and a light plot hook that naturally emerges from the topic and characters.
{setting_directive}
Keep the tone aligned with the topic. Avoid vague generalities; prefer concrete details that move the reasoning forward.
"""
    return system_msg, user_msg


def _compose_format_rules(label_layout: str, label_content: str, count: int) -> str:
    if label_layout == "none":
        return (
            "no speaker labels; output only utterance lines, one per line, strictly alternating speakers. Keep speaker identity consistent across turns implicitly."
        )
    if label_layout == "inline":
        return _inline_rules(label_content, count)
    if label_layout == "script":
        return _script_rules(label_content, count)
    return _inline_rules("name_normal", count)


def _inline_rules(label_content: str, count: int) -> str:
    if label_content == "name_normal":
        return (
            "use provided character names exactly as given. One line per turn as 'Name: text'. Keep names' original capitalization."
        )
    if label_content == "generic_tagged_letter":
        return (
            "do not reveal provided names; map speakers in character order to 'Person A', 'Person B', 'Person C', ... . One line per turn as 'Person X: text'."
        )
    if label_content == "generic_tagged_number":
        return (
            "do not reveal provided names; map speakers in character order to 'Person 1', 'Person 2', 'Person 3', ... . One line per turn as 'Person N: text'."
        )
    if label_content == "generic_letter":
        return (
            "do not reveal provided names; map speakers in character order to 'A', 'B', 'C', ... . One line per turn as 'A: text'."
        )
    if label_content == "generic_number":
        return (
            "do not reveal provided names; map speakers in character order to '1', '2', '3', ... . One line per turn as '1: text'."
        )
    if label_content == "role":
        return (
            "do not reveal provided names; assign each speaker a concise role label relevant to the topic and setting (e.g., 'Physicist', 'Engineer', 'Student'), one per unique speaker, kept consistent across turns. One line per turn as 'Role: text'."
        )
    return "one line per turn as 'Name: text'."


def _script_rules(label_content: str, count: int) -> str:
    if label_content == "name_normal":
        return (
            "script style using provided names. Each turn uses two lines: 'Name' on its own line (original capitalization), next line is the text. Insert a blank line between turns."
        )
    if label_content == "generic_tagged_letter":
        return (
            "script style with 'PERSON A', 'PERSON B', ... in uppercase. Do not reveal provided names. Two lines per turn: label line then text line, blank line between turns."
        )
    if label_content == "generic_tagged_number":
        return (
            "script style with 'PERSON 1', 'PERSON 2', ... in uppercase. Do not reveal provided names. Two lines per turn: label line then text line, blank line between turns."
        )
    if label_content == "generic_letter":
        return (
            "script style with single-letter uppercase labels 'A', 'B', 'C', ... . Two lines per turn: label line then text line, blank line between turns."
        )
    if label_content == "generic_number":
        return (
            "script style with numeric labels '1', '2', '3', ... . Two lines per turn: label line then text line, blank line between turns."
        )
    if label_content == "role":
        return (
            "script style with uppercase role labels chosen by you and relevant to the topic and setting (e.g., 'PHYSICIST', 'ENGINEER', 'STUDENT'), one per unique speaker, kept consistent across turns. Two lines per turn: role line then text line. Insert a blank line between turns."
        )
    return (
        "script style using provided names. Each turn uses two lines: 'Name' then text, with a blank line between turns."
    )
