"""The codebook: one YAML file that drives every engine and the human-readable document.

`config/codebook.yaml` defines constructs. Each construct is a Choice (one option from a fixed set)
or a Noul (a yes/no statement). Stance constructs share `stance_options` and carry a `claim`.
This module turns constructs into Jev questions, a Claude structured-output schema and prompt, and
Markdown documentation, so the three can never drift apart.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from typing import Any

from .config import load_yaml

NOUL_TRUE, NOUL_FALSE = "true", "false"


@dataclass
class Construct:
    name: str
    group: str
    primitive: str                      # choice | noul
    instructions: str
    options: dict[str, dict] = field(default_factory=dict)   # choice: name -> {what, not_for, examples}
    criteria: dict[str, dict] = field(default_factory=dict)  # noul: {"true": {...}, "false": {...}}
    claim: str | None = None

    @property
    def values(self) -> list[str]:
        return list(self.options) if self.primitive == "choice" else [NOUL_TRUE, NOUL_FALSE]

    @property
    def abstain(self) -> str | None:
        for cand in ("not_addressed", "not_applicable", "irrelevant", "other"):
            if cand in self.options:
                return cand
        return None


class Codebook:
    def __init__(self, data: dict | None = None) -> None:
        d = data or load_yaml("codebook.yaml")
        self.version: str = str(d["version"])
        # Publication constructs are versioned separately so their rubric can change without invalidating
        # the (expensive) post codes. Publication code runs record `pub_code_version`.
        self.publication_version: str = str(d.get("publication_version", d["version"]))
        self.domain: str = d["domain"].strip()
        self.stance_options: dict[str, dict] = d["stance_options"]
        self.constructs: list[Construct] = [self._build(c) for c in d["constructs"]]
        self.publication_constructs: list[Construct] = [self._build(c) for c in d.get("publication_constructs") or []]

    def _build(self, c: dict) -> Construct:
        prim = c["primitive"]
        group = c.get("group", "publication")
        if group == "stance":
            instr = c.get("instructions") or (
                "What is the author's own position on this claim? Claim: " + c["claim"].strip()
            )
            return Construct(c["name"], group, prim, instr, options=dict(self.stance_options), claim=c["claim"].strip())
        if prim == "choice":
            return Construct(c["name"], group, prim, c["instructions"].strip(), options=c["options"])
        return Construct(c["name"], group, prim, c["instructions"].strip(), criteria=c.get("criteria") or {})

    @property
    def pub_code_version(self) -> str:
        return f"{self.version}/pub{self.publication_version}"

    def code_version(self, entity_type: str) -> str:
        return self.pub_code_version if entity_type == "publication" else self.version

    # -- lookup ---------------------------------------------------------------
    def get(self, name: str) -> Construct:
        for c in self.constructs + self.publication_constructs:
            if c.name == name:
                return c
        raise KeyError(name)

    def by_group(self, *groups: str) -> list[Construct]:
        return [c for c in self.constructs if c.group in groups]

    # -- Jev ------------------------------------------------------------------
    def jev_questions(self, constructs: list[Construct], rng: random.Random | None = None) -> dict[str, dict]:
        """Questions keyed by construct name. With `rng`, Choice option order is permuted (position-bias
        control; see docs/jev.md §3). Option *names* never change, only their order in the criteria map.
        The domain definition is not repeated here: callers put it in the state once (see `jev_state`)."""
        qs: dict[str, dict] = {}
        for c in constructs:
            instr = c.instructions
            if c.primitive == "choice":
                names = list(c.options)
                if rng is not None:
                    rng.shuffle(names)
                crit = {n: _clean_criteria(c.options[n]) for n in names}
                qs[c.name] = {"type": "choice", "instructions": instr, "criteria": crit}
            else:
                q: dict[str, Any] = {"type": "noul", "instructions": instr}
                if c.criteria:
                    q["criteria"] = {k: _clean_criteria(v) for k, v in c.criteria.items()}
                qs[c.name] = q
        return qs

    def jev_state(self, state: dict) -> dict:
        """State with the domain definition prepended once, so every question's 'machine minds, as defined'
        resolves without repeating ~90 tokens per question."""
        return {"definitions": {"machine minds": self.domain}, **state}

    # -- Claude ---------------------------------------------------------------
    def claude_schema(self, constructs: list[Construct]) -> dict:
        props: dict[str, Any] = {}
        for c in constructs:
            props[c.name] = {
                "type": "object",
                "properties": {
                    "value": {"type": "string", "enum": c.values},
                    "evidence": {"type": "string", "description": "Verbatim quote from the post that best supports the value; empty string if the value is an abstain option or nothing in the text applies."},
                },
                "required": ["value", "evidence"],
                "additionalProperties": False,
            }
        return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}

    def claude_system(self, constructs: list[Construct], target: str = "post") -> str:
        lines = [
            "You are coding documents for a content analysis of writing about machine minds. Apply the codebook below exactly.",
            "Code the AUTHOR'S OWN position, not positions the author reports. Quote evidence verbatim from the text.",
            "When a claim does not come up, use the abstain option. Do not infer views the text does not express.",
            "",
            "Domain definition: " + self.domain,
            "",
            "Codebook version " + self.version,
            "",
        ]
        for c in constructs:
            lines.append(f"## {c.name} ({c.primitive})")
            lines.append(c.instructions)
            if c.primitive == "choice":
                for name, crit in c.options.items():
                    lines.append(f"- {name}: {crit.get('what','')}")
                    if crit.get("not_for"):
                        lines.append(f"    not for: {crit['not_for']}")
                    for ex in crit.get("examples") or []:
                        lines.append(f"    e.g. {ex}")
            else:
                lines.append("- true / false")
                for k, crit in (c.criteria or {}).items():
                    lines.append(f"    {k}: {crit.get('what','')}")
            lines.append("")
        lines.append(f"Return JSON with one object per construct: {{\"value\": ..., \"evidence\": ...}} for every construct listed above.")
        return "\n".join(lines)

    # -- docs -----------------------------------------------------------------
    def render_markdown(self) -> str:
        out = [f"# Codebook v{self.version}", "", "Generated from `config/codebook.yaml` by `mcreview codebook render`. Edit the YAML, not this file.", "",
               "## Domain", "", self.domain, ""]
        groups = [("relevance", "A. Relevance gate"), ("structure", "C. Genre and object"), ("stance", "B. Stance items"), ("argument", "E. Arguments")]
        for g, title in groups:
            out += [f"## {title}", ""]
            if g == "stance":
                out += ["Every stance item uses the same options:", ""]
                out += _options_md(self.stance_options)
                out += ["", "| Item | Claim |", "|---|---|"]
                out += [f"| `{c.name}` | {c.claim} |" for c in self.by_group(g)]
                out.append("")
                continue
            for c in self.by_group(g):
                out += [f"### `{c.name}` ({c.primitive})", "", c.instructions, ""]
                if c.primitive == "choice":
                    out += _options_md(c.options)
                elif c.criteria:
                    out += _options_md(c.criteria)
                out.append("")
        out += ["## Publication constructs", ""]
        for c in self.publication_constructs:
            out += [f"### `{c.name}` ({c.primitive})", "", c.instructions, ""] + _options_md(c.options) + [""]
        return "\n".join(out)


def _clean_criteria(crit: dict) -> dict:
    """Drop empty fields so the model is not shown 'not_for: ""'."""
    return {k: v for k, v in (crit or {}).items() if v not in (None, "", [])}


def _options_md(options: dict[str, dict]) -> list[str]:
    rows = ["| Option | What | Not for | Example |", "|---|---|---|---|"]
    for name, crit in options.items():
        ex = "; ".join(crit.get("examples") or [])
        rows.append(f"| `{name}` | {crit.get('what','')} | {crit.get('not_for','')} | {ex} |")
    return rows


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)
