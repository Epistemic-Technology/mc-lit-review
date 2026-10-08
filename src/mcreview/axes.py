"""Derived stance axes: five positions computed from the fourteen coded stance items.

The codebook's stance items are too granular to read patterns from (14 items x 6 options, most cells empty for
most posts), and the items are strongly redundant: when a post commits on both items of a pair, current
cognition agrees with understanding 95% of the time, current consciousness with emotions 91%, and so on
(measured on codebook 0.1.0 codes, 2026-10-08). This module collapses the items deterministically onto six
axes with a uniform level scheme, so the codes need not be re-run:

    yes            the author holds the pro-mind position on the axis
    yes_qualified  holds it with an axis-specific qualification (see AXES[...]["qualified"])
    unsure         explicit agnosticism (the agnostic option, or asserting that we cannot know)
    discussed      raises the question without a position
    no             holds the negative position
    not_addressed  the axis does not come up (reports_only counts here: no position of the author's own)

Each axis has a primary item and fallbacks. A committed value on the primary wins; fallbacks are consulted
only when the primary is uncommitted. `discusses` on any contributing item yields `discussed` when nothing
commits. The rules are the whole definition: change them here and re-export.
"""
from __future__ import annotations

from collections import Counter

LEVELS = ("yes", "yes_qualified", "unsure", "discussed", "no", "not_addressed")
COMMITTED = {"asserts": "yes", "denies": "no", "agnostic": "unsure"}

AXES: dict[str, dict] = {
    "experience_now": {
        "label": "Current LLMs have experience",
        "question": "Do current LLM-based systems have consciousness, feelings, or the capacity to suffer?",
        "items": ["current_conscious", "emotions", "cannot_know"],
        "qualified": None,
    },
    "cognition_now": {
        "label": "Current LLMs genuinely think",
        "question": "Do current LLM-based systems genuinely think, understand, or know?",
        "items": ["current_cognition", "understanding", "beliefs_knowledge"],
        "qualified": "Partly: yes on some capacities, no on others",
    },
    "agency_now": {
        "label": "Current LLMs have goals of their own",
        "question": "Do current LLM-based systems have genuine goals, preferences, or agency of their own?",
        "items": ["agency"],
        "qualified": None,
    },
    "possible": {
        "label": "AI could have a mind in principle",
        "question": "Could AI systems, of some architecture, be conscious or genuinely think?",
        "items": ["potential_conscious", "potential_cognition", "advance_needed"],
        "qualified": "Yes, but only after a major advance beyond current architectures",
    },
    "moral_status": {
        "label": "AI has moral status",
        "question": "Do AI systems' interests matter morally?",
        "items": ["moral_worth_current", "moral_worth_potential", "precaution"],
        "qualified": "Not now, but future AI could, or we should act with precaution regardless",
    },
    "serious": {
        "label": "AI consciousness is a serious question",
        "question": "Is AI consciousness a serious question, or hype, marketing, and anthropomorphism?",
        "items": ["deflationary"],
        "qualified": None,
    },
}
AXIS_ITEMS = {k: v["items"] for k, v in AXES.items()}


def _discussed(stance: dict, items: list[str]) -> str:
    return "discussed" if any(stance.get(i) == "discusses" for i in items) else "not_addressed"


def _first_committed(stance: dict, items: list[str]) -> str | None:
    for i in items:
        v = COMMITTED.get(stance.get(i) or "")
        if v:
            return v
    return None


def experience_now(s: dict) -> str:
    v = _first_committed(s, ["current_conscious", "emotions"])
    if v:
        return v
    if s.get("cannot_know") == "asserts":
        return "unsure"
    return _discussed(s, AXIS_ITEMS["experience_now"])


def cognition_now(s: dict) -> str:
    c = Counter(COMMITTED[s[i]] for i in AXIS_ITEMS["cognition_now"] if s.get(i) in COMMITTED)
    if c["yes"] and c["no"]:
        return "yes_qualified"
    if c["yes"]:
        return "yes"
    if c["no"]:
        return "no"
    if c["unsure"]:
        return "unsure"
    return _discussed(s, AXIS_ITEMS["cognition_now"])


def agency_now(s: dict) -> str:
    # Kept apart from cognition: goals and autonomy are the AI-safety framing, and a large group grants agency
    # while unsure about experience (2026-10-08 check: of 826 committed, 260 commit on no other cognition item).
    v = COMMITTED.get(s.get("agency") or "")
    return v or _discussed(s, AXIS_ITEMS["agency_now"])


def possible(s: dict) -> str:
    v = _first_committed(s, ["potential_conscious", "potential_cognition"])
    adv = s.get("advance_needed")
    if v == "yes":
        return "yes_qualified" if adv == "asserts" else "yes"
    if v:
        return v
    # advance_needed alone: "a major advance would be needed first" presupposes possibility;
    # denying it (current architectures are not in principle insufficient) is a yes on the current path.
    if adv == "asserts":
        return "yes_qualified"
    if adv == "denies":
        return "yes"
    if adv == "agnostic":
        return "unsure"
    return _discussed(s, AXIS_ITEMS["possible"])


def moral_status(s: dict) -> str:
    cur = COMMITTED.get(s.get("moral_worth_current") or "")
    later = any(s.get(i) == "asserts" for i in ("moral_worth_potential", "precaution"))
    if cur == "yes":
        return "yes"
    if cur in ("no", "unsure"):
        return "yes_qualified" if later else cur
    if later:
        return "yes_qualified"
    v = _first_committed(s, ["moral_worth_potential", "precaution"])
    if v:
        return v
    return _discussed(s, AXIS_ITEMS["moral_status"])


def serious(s: dict) -> str:
    v = s.get("deflationary")
    if v == "asserts":
        return "no"
    if v == "denies":
        return "yes"
    if v == "agnostic":
        return "unsure"
    return _discussed(s, AXIS_ITEMS["serious"])


RULES = {"experience_now": experience_now, "cognition_now": cognition_now, "agency_now": agency_now, "possible": possible, "moral_status": moral_status, "serious": serious}


def derive(stance: dict) -> dict[str, str]:
    """Map one post's stance codes ({item: option}) to {axis: level}."""
    return {axis: fn(stance) for axis, fn in RULES.items()}
