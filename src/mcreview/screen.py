"""Loose keyword matcher over the query bank. Used only for source gating in citation rounds:
it never decides inclusion, only whether an admitted post may propagate references."""
from __future__ import annotations

import re


class Screen:
    def __init__(self, terms: list[tuple[str, str]]) -> None:
        self.patterns: list[tuple[str, re.Pattern[str]]] = []
        for _facet, term in terms:
            words = [re.escape(w) for w in term.split()]
            self.patterns.append((term, re.compile(r"\b" + r"\W+".join(words) + r"\b", re.IGNORECASE)))

    def score(self, text: str) -> tuple[int, list[str]]:
        matched = [term for term, pat in self.patterns if pat.search(text)]
        return len(matched), matched
