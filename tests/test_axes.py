"""Derived stance axes: the collapsing rules in mcreview.axes."""
from mcreview.axes import AXES, LEVELS, derive


def _s(**kw):
    return {k: kw.get(k, "not_addressed") for a in AXES.values() for k in a["items"]}


def test_every_axis_yields_a_level():
    out = derive(_s())
    assert set(out) == set(AXES) and all(v == "not_addressed" for v in out.values())
    assert all(v in LEVELS for v in derive(_s(current_conscious="asserts", deflationary="discusses")).values())


def test_experience_primary_wins_then_emotions_then_cannot_know():
    assert derive(_s(current_conscious="denies", emotions="asserts"))["experience_now"] == "no"
    assert derive(_s(emotions="asserts"))["experience_now"] == "yes"
    assert derive(_s(current_conscious="discusses", cannot_know="asserts"))["experience_now"] == "unsure"
    assert derive(_s(current_conscious="reports_only", emotions="discusses"))["experience_now"] == "discussed"
    assert derive(_s(current_conscious="reports_only"))["experience_now"] == "not_addressed"


def test_cognition_mixed_is_qualified():
    assert derive(_s(current_cognition="asserts", understanding="denies"))["cognition_now"] == "yes_qualified"
    assert derive(_s(understanding="denies", beliefs_knowledge="denies"))["cognition_now"] == "no"
    assert derive(_s(current_cognition="agnostic", beliefs_knowledge="asserts"))["cognition_now"] == "yes"
    assert derive(_s(current_cognition="agnostic"))["cognition_now"] == "unsure"


def test_agency_is_its_own_axis():
    out = derive(_s(current_cognition="asserts", agency="denies"))
    assert out["cognition_now"] == "yes" and out["agency_now"] == "no"
    assert derive(_s(agency="asserts"))["agency_now"] == "yes" and derive(_s(agency="asserts"))["cognition_now"] == "not_addressed"
    assert derive(_s(agency="discusses"))["agency_now"] == "discussed"
    assert derive(_s(agency="reports_only"))["agency_now"] == "not_addressed"


def test_possible_with_advance_needed():
    assert derive(_s(potential_conscious="asserts", advance_needed="asserts"))["possible"] == "yes_qualified"
    assert derive(_s(potential_conscious="asserts", advance_needed="denies"))["possible"] == "yes"
    assert derive(_s(potential_conscious="denies", advance_needed="asserts"))["possible"] == "no"
    assert derive(_s(potential_cognition="asserts"))["possible"] == "yes"
    assert derive(_s(advance_needed="asserts"))["possible"] == "yes_qualified"
    assert derive(_s(advance_needed="discusses"))["possible"] == "discussed"


def test_moral_status_precaution_and_future():
    assert derive(_s(moral_worth_current="asserts", precaution="denies"))["moral_status"] == "yes"
    assert derive(_s(moral_worth_current="agnostic", precaution="asserts"))["moral_status"] == "yes_qualified"
    assert derive(_s(moral_worth_current="denies", moral_worth_potential="asserts"))["moral_status"] == "yes_qualified"
    assert derive(_s(moral_worth_current="denies"))["moral_status"] == "no"
    assert derive(_s(moral_worth_potential="asserts"))["moral_status"] == "yes_qualified"
    assert derive(_s(precaution="denies"))["moral_status"] == "no"
    assert derive(_s(moral_worth_current="discusses"))["moral_status"] == "discussed"


def test_serious_is_deflationary_reversed():
    assert derive(_s(deflationary="asserts"))["serious"] == "no"
    assert derive(_s(deflationary="denies"))["serious"] == "yes"
    assert derive(_s(deflationary="discusses"))["serious"] == "discussed"
