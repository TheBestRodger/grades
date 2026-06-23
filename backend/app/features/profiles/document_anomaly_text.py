from __future__ import annotations

import json
import re
from typing import Any


TOKEN_PATTERN = re.compile(r"[A-Za-zА-Яа-яЁё0-9]{4,}")
STOPWORDS = {
    "без",
    "более",
    "будет",
    "были",
    "ваша",
    "ваши",
    "весь",
    "всех",
    "если",
    "есть",
    "или",
    "как",
    "надо",
    "него",
    "нет",
    "нужно",
    "однако",
    "отдел",
    "очень",
    "при",
    "свои",
    "своих",
    "также",
    "тест",
    "тестов",
    "того",
    "только",
    "чтобы",
    "это",
    "этой",
    "этот",
    "для",
    "демо",
    "демонстрац",
    "демонстрационн",
    "что",
    "the",
    "and",
    "with",
}
ENDINGS = (
    "иями",
    "ями",
    "ами",
    "ого",
    "ему",
    "ыми",
    "ими",
    "ых",
    "их",
    "ая",
    "яя",
    "ое",
    "ее",
    "ые",
    "ие",
    "ый",
    "ий",
    "ой",
    "ам",
    "ям",
    "ах",
    "ях",
    "ов",
    "ев",
    "ом",
    "ем",
    "ую",
    "юю",
    "а",
    "я",
    "ы",
    "и",
    "е",
    "у",
)


def revision_answers(revision) -> dict[str, Any]:
    try:
        loaded = json.loads(revision.answers_json or "{}")
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def answers_text(answers: dict[str, Any], keys: list[str]) -> str:
    return " ".join(flatten_answer(answers.get(key, "")) for key in keys)


def flatten_answer(value: Any) -> str:
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return value
        return flatten_answer(decoded)
    if isinstance(value, list):
        return " ".join(flatten_answer(item) for item in value)
    if isinstance(value, dict):
        return " ".join(flatten_answer(item) for item in value.values())
    if value is None:
        return ""
    return str(value)


def tokens(text: str) -> set[str]:
    result = set()
    for raw in TOKEN_PATTERN.findall(text.replace("ё", "е").lower()):
        token = stem(raw)
        if token and token not in STOPWORDS:
            result.add(token)
    return result


def stem(token: str) -> str:
    for ending in ENDINGS:
        if len(token) > len(ending) + 4 and token.endswith(ending):
            return token[: -len(ending)]
    return token


_revision_answers = revision_answers
_answers_text = answers_text
_flatten_answer = flatten_answer
_tokens = tokens
_stem = stem
