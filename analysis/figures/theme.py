"""Shared chart theme: the reference palette from the dataviz method, applied to Altair.

Light-mode values; the site renders its own dark steps from the same slots. Marks are thin, grid and
axes are solid hairlines one step off the surface, text wears text tokens, never the series colour.
"""
from __future__ import annotations

import altair as alt

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

# Categorical slots, fixed order (validated adjacent pairs; first three validate all-pairs).
SLOTS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = SLOTS
GRAY = "#898781"
GRAY_LIGHT = "#c3c2b7"
NEUTRAL = "#f0efec"   # diverging midpoint

# Entity colours follow the entity across every chart (never re-assigned by rank).
GROUP_COLORS = {"general": BLUE, "ai_field": ORANGE, "academic": AQUA, "journalism": YELLOW, "religion": MAGENTA}
GROUP_LABELS = {"general": "General and culture", "ai_field": "AI field", "academic": "Academic", "journalism": "Journalism and politics", "religion": "Religion and spirituality"}
STANCE_COLORS = {"denies": RED, "agnostic": GRAY, "discusses": GRAY_LIGHT, "asserts": BLUE}
STANCE_LABELS = {"denies": "Denies", "agnostic": "Agnostic", "discusses": "Discusses, no position", "asserts": "Asserts"}
TIER_COLORS = {"academic": AQUA, "lab": ORANGE, "substack": BLUE, "press": YELLOW, "other": GRAY}
TIER_LABELS = {"academic": "Academic", "lab": "AI lab", "substack": "Substack", "press": "Press", "other": "Other web"}

FONT = "system-ui, -apple-system, 'Segoe UI', sans-serif"


def theme() -> dict:
    return {
        "config": {
            "background": SURFACE,
            "font": FONT,
            "title": {"font": FONT, "fontSize": 18, "fontWeight": 600, "color": INK, "anchor": "start", "subtitleColor": INK2, "subtitleFontSize": 13, "subtitlePadding": 6, "offset": 14},
            "axis": {"labelFont": FONT, "titleFont": FONT, "labelColor": INK2, "titleColor": MUTED, "titleFontWeight": 400, "gridColor": GRID, "gridWidth": 1, "domainColor": AXIS, "tickColor": AXIS, "labelFontSize": 12, "titleFontSize": 12, "labelPadding": 6},
            "axisX": {"grid": False},
            "axisY": {"domain": False, "ticks": False},
            "legend": {"labelFont": FONT, "titleFont": FONT, "labelColor": INK2, "titleColor": MUTED, "labelFontSize": 12, "titleFontSize": 12, "symbolType": "square", "symbolSize": 80, "orient": "top", "direction": "horizontal", "titleOrient": "left"},
            "view": {"stroke": None},
            "bar": {"cornerRadiusEnd": 4},
            "line": {"strokeWidth": 2, "strokeJoin": "round", "strokeCap": "round"},
            "point": {"size": 64, "filled": True},
            "text": {"font": FONT, "fontSize": 12, "color": INK2},
            "header": {"labelFont": FONT, "titleFont": FONT, "labelColor": INK, "labelFontSize": 13, "labelFontWeight": 600, "titleColor": MUTED},
            "range": {"category": SLOTS},
        }
    }


def register() -> None:
    alt.themes.register("mcreview", theme)
    alt.themes.enable("mcreview")
