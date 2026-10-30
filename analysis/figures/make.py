"""Static figures for the post, from the exported data (site/src/data). Writes PNG (1200 px wide, 2x) and
SVG to figures/, and the Vega-Lite spec to site/src/charts/ so the site can render the same chart live.

Run: uv run python analysis/figures/make.py [name ...]
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import altair as alt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import theme as T  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "site" / "src" / "data"
FIG = ROOT / "figures"
SPEC = ROOT / "site" / "src" / "charts"
WIDTH = 600   # CSS px; rendered at 2x -> 1200 px wide PNG

T.register()


def load(name: str):
    return json.loads((DATA / f"{name}.json").read_text())


def save(chart: alt.Chart, name: str) -> None:
    FIG.mkdir(exist_ok=True)
    SPEC.mkdir(parents=True, exist_ok=True)
    chart.save(str(FIG / f"{name}.png"), scale_factor=2)
    chart.save(str(FIG / f"{name}.svg"))
    (SPEC / f"{name}.vl.json").write_text(chart.to_json())
    print("wrote", name)


# ---------------------------------------------------------------- stance landscape (diverging stacked bar)

def _diverging_rows(table: dict, items: list[dict], facet: str | None = None) -> list[dict]:
    """Likert layout: denies on the left, asserts on the right, the two neutral options straddling zero.
    Shares are of posts that address the claim (not_addressed and reports_only excluded)."""
    rows = []
    for it in items:
        c = table[it["name"]]
        n = c["denies"] + c["agnostic"] + c["discusses"] + c["asserts"]
        if n == 0:
            continue
        sh = {k: c[k] / n for k in ("denies", "agnostic", "discusses", "asserts")}
        neutral = sh["agnostic"] + sh["discusses"]
        left = -(sh["denies"] + neutral / 2)
        x = left
        for k in ("denies", "agnostic", "discusses", "asserts"):
            rows.append({"item": it["label"], "option": k, "x0": x, "x1": x + sh[k], "share": sh[k], "n": n, "count": c[k],
                         "addressing": n, "facet": facet, "asserts_share": sh["asserts"], "denies_share": sh["denies"]})
            x += sh[k]
    return rows


ITEM_LABELS = {
    "current_conscious": "Current LLMs are conscious", "potential_conscious": "AI could be conscious in principle",
    "current_cognition": "Current LLMs genuinely think", "potential_cognition": "AI could genuinely think",
    "understanding": "LLMs genuinely understand", "beliefs_knowledge": "LLMs have beliefs or knowledge",
    "emotions": "LLMs have emotions or can suffer", "agency": "LLMs have goals or agency of their own",
    "moral_worth_current": "Current LLMs have moral worth", "moral_worth_potential": "Future AI could have moral worth",
    "advance_needed": "Current architectures are insufficient", "cannot_know": "We cannot know whether AI is conscious",
    "precaution": "Act with precaution regardless", "deflationary": "AI consciousness talk is hype",
}


def _axis_rows(table: dict, axes: list[dict], facet: str | None = None) -> list[dict]:
    """Same Likert layout for the derived axes (mcreview.axes): no on the left, yes and qualified yes on the
    right, unsure and discussed straddling zero. Shares are of posts addressing the axis."""
    rows = []
    for ax in axes:
        c = table[ax["name"]]
        keys = ("no", "unsure", "discussed", "yes_qualified", "yes")
        n = sum(c[k] for k in keys)
        if n == 0:
            continue
        sh = {k: c[k] / n for k in keys}
        x = -(sh["no"] + (sh["unsure"] + sh["discussed"]) / 2)
        for k in keys:
            rows.append({"item": ax["label"], "option": k, "x0": x, "x1": x + sh[k], "share": sh[k], "n": n, "count": c[k],
                         "addressing": n, "facet": facet, "asserts_share": sh["yes"] + sh["yes_qualified"], "denies_share": sh["no"]})
            x += sh[k]
    return rows


AXIS_SCHEME = {"colors": T.AXIS_COLORS, "labels": T.AXIS_LABELS, "pos": "yes", "neg": "no", "x_title": "Share of posts addressing the question"}


def _stance_chart(rows: list[dict], title: str, subtitle: str, height_per_row: int = 26, facet_col: str | None = None, columns: int = 1, scheme: dict | None = None) -> alt.Chart:
    sc = scheme or {"colors": T.STANCE_COLORS, "labels": T.STANCE_LABELS, "pos": "asserts", "neg": "denies", "x_title": "Share of posts addressing the claim"}
    lim = sc.get("limit", 1.0)
    ticks = [v for v in (-1, -0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75, 1) if abs(v) <= lim] if lim == 1.0 else sorted({round(v * lim / 2, 3) for v in (-2, -1, 0, 1, 2)})
    df = pd.DataFrame(rows)
    order = (df[df.option == sc["pos"]].groupby("item")["asserts_share"].mean().sort_values(ascending=False).index.tolist())
    # In facet mode every layer must be data-less so the facet partition applies; the data goes on the facet.
    src = alt.Chart(df) if facet_col is None else alt.Chart()
    base = src.encode(
        y=alt.Y("item:N", sort=order, title=None, axis=alt.Axis(labelLimit=260)),
    )
    bars = base.mark_bar(height=18, cornerRadiusEnd=0).encode(
        x=alt.X("x0:Q", title=sc["x_title"], axis=alt.Axis(format="%", values=ticks, labelExpr="format(abs(datum.value), '.0%')", grid=True), scale=alt.Scale(domain=[-lim, lim])),
        x2="x1:Q",
        color=alt.Color("option:N", scale=alt.Scale(domain=list(sc["colors"]), range=list(sc["colors"].values())),
                        legend=alt.Legend(title="Author's position", labelExpr=json.dumps(sc["labels"]) + "[datum.label]")),
        stroke=alt.value(T.SURFACE), strokeWidth=alt.value(2),
        tooltip=[alt.Tooltip("item:N", title="Claim"), alt.Tooltip("option:N", title="Position"), alt.Tooltip("count:Q", title="Posts"), alt.Tooltip("share:Q", format=".0%", title="Share"), alt.Tooltip("addressing:Q", title="Posts addressing")],
    )
    # every layer shares `df` (a facet needs one data source): the zero rule and the end labels are filters on it
    zero = src.mark_rule(color=T.AXIS, strokeWidth=1).encode(x=alt.datum(0))
    lab_r = src.transform_filter(alt.datum.option == sc["pos"]).mark_text(align="left", dx=6, color=T.INK2, fontSize=11).encode(
        y=alt.Y("item:N", sort=order), x="x1:Q", text=alt.Text("asserts_share:Q", format=".0%"))
    lab_l = src.transform_filter(alt.datum.option == sc["neg"]).mark_text(align="right", dx=-6, color=T.INK2, fontSize=11).encode(
        y=alt.Y("item:N", sort=order), x="x0:Q", text=alt.Text("denies_share:Q", format=".0%"))
    if facet_col is None:
        n_lab = src.transform_filter(alt.datum.option == sc["pos"]).mark_text(align="left", color=T.MUTED, fontSize=10).encode(
            y=alt.Y("item:N", sort=order), x=alt.value(WIDTH + 44), text=alt.Text("addressing:Q", format=",d"))
        if sc.get("legend_title"):
            bars = bars.encode(color=alt.Color("option:N", scale=alt.Scale(domain=list(sc["colors"]), range=list(sc["colors"].values())), legend=alt.Legend(title=sc["legend_title"], labelExpr=json.dumps(sc["labels"]) + "[datum.label]")))
        chart = alt.layer(bars, zero, lab_l, lab_r, n_lab).properties(width=WIDTH, height=height_per_row * len(order), title=alt.Title(title, subtitle=subtitle))
    else:
        chart = alt.layer(bars, zero, lab_l, lab_r).properties(width=WIDTH // columns - 40, height=height_per_row * len(order)).facet(
            facet=alt.Facet(f"{facet_col}:N", title=None, sort=list(T.GROUP_LABELS.values())), columns=columns, data=df, title=alt.Title(title, subtitle=subtitle))
    return chart


def stance_landscape():
    st = load("stance")
    items = [{"name": it["name"], "label": ITEM_LABELS.get(it["name"], it["name"])} for it in st["items"]]
    rows = _diverging_rows(st["overall"], items)
    n = st["n"]
    chart = _stance_chart(rows, "What Substack writers say about machine minds",
                          f"Authors' own positions in {n:,} relevant posts, as a share of posts that address each claim. Right-hand figure: posts addressing it.")
    save(chart, "stance_landscape")


def stance_by_group():
    st = load("stance")
    head = ["current_conscious", "potential_conscious", "current_cognition", "moral_worth_current"]
    items = [{"name": k, "label": ITEM_LABELS[k]} for k in head]
    rows = []
    for g, table in st["by_group"].items():
        rows += _diverging_rows(table, items, facet=T.GROUP_LABELS[g])
    chart = _stance_chart(rows, "Positions differ by who is writing", "Share of posts addressing each claim, by publication type. Agnostic and non-committal posts straddle the centre.",
                          facet_col="facet", columns=1, height_per_row=24)
    save(chart, "stance_by_group")


# ---------------------------------------------------------------- derived axes (mcreview.axes)

def _axes_meta():
    st = load("stance_axes")
    return st, [{"name": a["name"], "label": a["label"]} for a in st["axes"]]


def axes_landscape():
    st, axes = _axes_meta()
    rows = _axis_rows(st["overall"], axes)
    chart = _stance_chart(rows, "Six positions on machine minds",
                          [f"Authors' own positions in {st['n']:,} relevant posts, as a share of posts addressing each question. Right: posts addressing it.",
                           "'Yes, qualified' is question-specific: partly, after a major advance, or future AI / precaution."],
                          scheme=AXIS_SCHEME, height_per_row=30)
    save(chart, "axes_landscape")


def axes_by_group():
    st, axes = _axes_meta()
    rows = []
    for g, table in st["by_group"].items():
        rows += _axis_rows(table, axes, facet=T.GROUP_LABELS[g])
    chart = _stance_chart(rows, "Positions by who is writing", "Share of posts addressing each question, by publication type. Unsure and non-committal posts straddle the centre.",
                          facet_col="facet", columns=1, height_per_row=24, scheme=AXIS_SCHEME)
    save(chart, "axes_by_group")


def axes_over_time(min_n: int = 5):
    """Composition by quarter for the three 'now' axes, on the recency-unbiased channels. No event markers."""
    st, axes = _axes_meta()
    keys = ["no", "unsure", "discussed", "yes_qualified", "yes"]
    label_of = {a["name"]: a["label"] for a in axes}
    axes_shown = ("experience_now", "cognition_now", "agency_now")
    # Start at the first quarter from which every shown axis stays at or above the threshold, so the series is
    # unbroken: an omitted quarter in the middle would make the area interpolate across a gap. The threshold is low
    # enough that the series runs from the start of the corpus (2024Q1); the early quarters are small, and the
    # tooltip shows the count behind each share.
    qs = sorted(st["by_quarter_unbiased"])
    ok = [all(sum(st["by_quarter_unbiased"][q][ax][k] for k in keys) >= min_n for ax in axes_shown) for q in qs]
    start = next(i for i in range(len(qs)) if all(ok[i:]))
    rows = []
    for q in qs[start:]:
        for ax in axes_shown:
            c = st["by_quarter_unbiased"][q][ax]
            n = sum(c[k] for k in keys)
            for k in keys:
                rows.append({"quarter": q, "axis": label_of[ax], "option": k, "share": c[k] / n, "count": c[k], "n": n})
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["quarter"].str[:4] + "-" + ((df["quarter"].str[5].astype(int) - 1) * 3 + 2).astype(str).str.zfill(2) + "-15")
    area = alt.Chart(df).mark_area(interpolate="monotone", opacity=0.85, stroke=T.SURFACE, strokeWidth=1.5).encode(
        x=alt.X("date:T", title=None, axis=alt.Axis(format="%b %Y", grid=False, labelAngle=0, labelPadding=18)),
        y=alt.Y("share:Q", stack="normalize", title="Share of posts", axis=alt.Axis(format="%", grid=True)),
        color=alt.Color("option:N", scale=alt.Scale(domain=keys, range=[T.AXIS_COLORS[k] for k in keys]), sort=keys,
                        legend=alt.Legend(title="Author's position", labelExpr=json.dumps(T.AXIS_LABELS) + "[datum.label]")),
        order=alt.Order("option:N", sort="ascending"),
        tooltip=[alt.Tooltip("axis:N", title="Question"), alt.Tooltip("quarter:N", title="Quarter"), alt.Tooltip("option:N", title="Position"), alt.Tooltip("count:Q", title="Posts"), alt.Tooltip("share:Q", format=".0%", title="Share"), alt.Tooltip("n:Q", title="Posts addressing")])
    first_q, last_q = df.quarter.min(), df.quarter.max()
    chart = area.properties(width=WIDTH, height=170).facet(
        row=alt.Row("axis:N", title=None, sort=[label_of[a] for a in axes_shown], header=alt.Header(labelAngle=0, labelAlign="left", labelOrient="top")),
        title=alt.Title("Positions over time", subtitle=[f"Quarterly composition, {first_q} to {last_q}, among the {st['n_unbiased']:,} relevant posts found through web search or citation.",
                                                         f"Substack's own search is recency-skewed and excluded. The first three quarters have fewer than 20 posts per question."]))
    save(chart, "axes_over_time")


def _profile_chart(st: dict, key: str, other: str, other_title: str, title: str, subtitle: list[str], name: str):
    """Experience x another 'now' axis, counts of posts committed on both."""
    lv = {"yes": "Yes", "yes_qualified": "Partly", "unsure": "Unsure", "no": "No"}
    rows = [{"experience": lv[r["experience_now"]], "other": lv[r[other]], "n": r["n"]} for r in st[key] if r["experience_now"] in lv and r[other] in lv]
    df = pd.DataFrame(rows)
    total = int(df.n.sum())
    df["share"] = df.n / total
    xo, yo = [k for k in ["No", "Unsure", "Partly", "Yes"] if k in set(df.other)], ["Yes", "Unsure", "No"]
    cells = alt.Chart(df).mark_rect(stroke=T.SURFACE, strokeWidth=2).encode(
        x=alt.X("other:N", sort=xo, title=other_title, axis=alt.Axis(labelAngle=0, orient="top", labelPadding=6)),
        y=alt.Y("experience:N", sort=yo, title="Current LLMs have experience"),
        color=alt.Color("n:Q", scale=alt.Scale(range=["#cde2fb", "#0d366b"]), legend=None),
        tooltip=[alt.Tooltip("experience:N", title="Experience"), alt.Tooltip("other:N", title=other_title), alt.Tooltip("n:Q", title="Posts"), alt.Tooltip("share:Q", format=".0%", title="Share of committed")])
    text = alt.Chart(df).mark_text(fontSize=13, fontWeight=600).encode(
        x=alt.X("other:N", sort=xo), y=alt.Y("experience:N", sort=yo), text=alt.Text("n:Q", format=",d"),
        color=alt.condition(alt.datum.n > total * 0.12, alt.value(T.SURFACE), alt.value(T.INK)))
    chart = alt.layer(cells, text).properties(width=75 * len(xo), height=200, title=alt.Title(title, subtitle=[s.format(total=f"{total:,}") for s in subtitle]))
    save(chart, name)


def axes_profile():
    st, _ = _axes_meta()
    _profile_chart(st, "profile_experience_cognition", "cognition_now", "Current LLMs genuinely think", "Thinking without experience",
                   ["Posts with a position on both questions ({total}). The off-diagonal 'thinks, but not conscious' cells", "are a real camp; the reverse is nearly empty."], "axes_profile")


def axes_profile_agency():
    st, _ = _axes_meta()
    _profile_chart(st, "profile_experience_agency", "agency_now", "Current LLMs have goals of their own", "Goals without experience",
                   ["Posts with a position on both questions ({total}). Granting goals while unsure about experience", "is the AI-safety framing; the reverse corner is nearly empty."], "axes_profile_agency")


# ---------------------------------------------------------------- arguments: frequency

ARG_LABELS = {
    "arg_chinese_room": "Chinese room", "arg_stochastic_parrot": "Stochastic parrot / next-token", "arg_hard_problem": "Hard problem",
    "arg_other_minds": "Other minds / behavioural evidence", "arg_self_report": "Self-reports unreliable", "arg_functionalism": "Functionalism / substrate independence",
    "arg_biological": "Biology or embodiment required", "arg_theory_indicators": "Theory-based indicators", "arg_emergence": "Emergence from scale",
    "arg_anthropomorphism": "Anthropomorphism warning", "arg_precaution_moral_circle": "Precaution / moral circle", "arg_mimicry": "Mimicry of training data",
    "arg_panpsychism_illusionism": "Panpsychism or illusionism",
}


def arguments_frequency():
    """How often each argument type appears across relevant posts, most common first."""
    args = load("arguments")
    df = pd.DataFrame([{"label": ARG_LABELS.get(a["name"], a["name"]), "share": a["share"], "n": a["n"], "cited": a["share_cited"]} for a in args])
    order = df.sort_values("share", ascending=False)["label"].tolist()
    tips = [alt.Tooltip("label:N", title="Argument"), alt.Tooltip("n:Q", title="Posts"), alt.Tooltip("share:Q", format=".0%", title="Share"), alt.Tooltip("cited:Q", format=".0%", title="Share cited by another publication")]
    y = alt.Y("label:N", sort=order, title=None, axis=alt.Axis(labelLimit=280))
    freq = alt.Chart(df).mark_bar(height=14, color=T.BLUE).encode(y=y, x=alt.X("share:Q", title="Share of relevant posts", axis=alt.Axis(format="%", grid=True, tickCount=4)), tooltip=tips)
    freq_lab = alt.Chart(df).mark_text(align="left", dx=5, fontSize=11, color=T.INK2).encode(y=y, x="share:Q", text=alt.Text("share:Q", format=".0%"))
    chart = alt.layer(freq, freq_lab).properties(width=WIDTH - 180, height=18 * len(df), title=alt.Title("Which arguments are common",
                      subtitle="Thirteen argument types coded present or absent per relevant post; a post can use several."))
    save(chart, "arguments_frequency")


# ---------------------------------------------------------------- features of the systems (codebook 0.4.0)

FEATURE_COLORS = {"against": T.RED, "both_or_neutral": T.GRAY_LIGHT, "for": T.BLUE}
FEATURE_DIR_LABELS = {"against": "Against a mind", "both_or_neutral": "Both ways or no direction", "for": "Toward a mind"}


def features_landscape():
    """Diverging bar per feature: share of coded relevant posts pointing to it, split by direction. Unlike the stance
    charts the shares are of all coded posts, so bar length is frequency and the split is direction."""
    ft = load("features")
    n = ft["n_coded"] or 1
    rows = []
    for f in ft["features"]:
        sh = {d: f["direction"][d] / n for d in ("against", "both_or_neutral", "for")}
        x = -(sh["against"] + sh["both_or_neutral"] / 2)
        for d in ("against", "both_or_neutral", "for"):
            rows.append({"item": f["label"], "option": d, "x0": x, "x1": x + sh[d], "share": sh[d], "n": n, "count": f["direction"][d],
                         "addressing": f["n"], "facet": None, "asserts_share": sh["for"], "denies_share": sh["against"]})
            x += sh[d]
    # Axis limit: the widest bar plus room for its percentage label, rounded up to the next 5%.
    lim = max(0.1, math.ceil((max(max(abs(r["x0"]), abs(r["x1"])) for r in rows) + 0.08) / 0.05) * 0.05)
    scheme = {"colors": FEATURE_COLORS, "labels": FEATURE_DIR_LABELS, "pos": "for", "neg": "against", "x_title": "Share of relevant posts pointing to the feature", "limit": lim, "legend_title": "Cited as"}
    chart = _stance_chart(rows, "Which features of the systems get pointed to, and which way",
                          f"Share of {n:,} coded relevant posts citing each feature as bearing on machine minds. Right: as reason to think the system has or could have a mind; left: as reason it lacks one. Count of citing posts at right.",
                          scheme=scheme)
    save(chart, "features_landscape")


def features_over_time(min_n: int = 15):
    """Share of recency-unbiased relevant posts per quarter that point to each feature, faceted by family. Quarters
    before the first run of quarters with at least `min_n` coded posts are dropped so every series is unbroken."""
    ft = load("features")
    qn = ft["quarter_n_unbiased"]
    qs = sorted(qn)
    ok = [qn[q] >= min_n for q in qs]
    start = next((i for i in range(len(qs)) if all(ok[i:])), len(qs) - 1)
    fam_label = {f["key"]: f["label"] for f in ft["families"]}
    rows = []
    for f in ft["features"]:
        for q in qs[start:]:
            c = f["by_quarter_unbiased"].get(q, {})
            cited = sum(c.values())
            rows.append({"quarter": q, "family": fam_label[f["family"]], "feature": f["label"], "share": cited / qn[q], "count": cited, "n": qn[q], "for": c.get("for", 0), "against": c.get("against", 0)})
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["quarter"].str[:4] + "-" + ((df["quarter"].str[5].astype(int) - 1) * 3 + 2).astype(str).str.zfill(2) + "-15")
    ymax = max(0.1, float(df.share.max()) * 1.05)
    panels = []
    # One panel per family with its own colour scale and legend: thirteen series on one legend is unreadable, and a
    # shared scale would recycle the eight slots. Colours therefore mean different features in different panels.
    for i, fam in enumerate(ft["families"]):
        feats = [ft["labels"][n] for n in fam["features"]]
        sub = df[df.family == fam["label"]]
        last = i == len(ft["families"]) - 1
        line = alt.Chart(sub).mark_line(interpolate="monotone", point=alt.OverlayMarkDef(size=30)).encode(
            x=alt.X("date:T", title=None, axis=alt.Axis(format="%b %Y", grid=False, labelAngle=0, labelPadding=18, labels=last, ticks=last)),
            y=alt.Y("share:Q", title="Share of posts", axis=alt.Axis(format="%", grid=True, tickCount=4), scale=alt.Scale(domain=[0, ymax])),
            color=alt.Color("feature:N", scale=alt.Scale(domain=feats, range=T.SLOTS[:len(feats)]), legend=alt.Legend(title=fam["label"], orient="right", direction="vertical", symbolType="stroke", labelLimit=220, titleOrient="top")),
            tooltip=[alt.Tooltip("feature:N", title="Feature"), alt.Tooltip("quarter:N", title="Quarter"), alt.Tooltip("count:Q", title="Posts citing"), alt.Tooltip("share:Q", format=".0%", title="Share"), alt.Tooltip("for:Q", title="For"), alt.Tooltip("against:Q", title="Against"), alt.Tooltip("n:Q", title="Posts in quarter")])
        panels.append(line.properties(width=WIDTH - 60, height=140))
    first_q, last_q = df.quarter.min(), df.quarter.max()
    chart = alt.vconcat(*panels, spacing=16).resolve_scale(color="independent").properties(
        title=alt.Title("Features pointed to, over time", subtitle=[f"Share of relevant posts per quarter citing each feature, {first_q} to {last_q}, among the {ft['n_unbiased']:,} coded posts found through web search or citation.",
                                                                     f"Substack's own search is recency-skewed and excluded; quarters with fewer than {min_n} posts are omitted. One panel per family, each with its own colours."]))
    save(chart, "features_over_time")


SIDE_COLORS = {"deny": T.RED, "affirm": T.BLUE}
SIDE_LABELS = {"deny": "Denying posts: features cited against a mind", "affirm": "Affirming posts: features cited toward a mind"}


def features_sides():
    """For each feature, the share of denying posts that cite it against a mind (left) and of affirming posts that
    cite it toward one (right), among the side's posts citing at least one feature their own way, sorted by the
    denying side. A post's side comes from the six questions: yes on at least one and no on none affirms; the
    reverse denies (see export.feature_tables)."""
    ft = load("features")
    S = ft["sides"]
    rows = []
    for s in ("deny", "affirm"):
        d = S[s]
        c = d["citing"] or 1
        for f, cnt in d["features"].items():
            sh = cnt / c
            rows.append({"feature": ft["labels"][f], "side": s, "share": sh, "x": -sh if s == "deny" else sh, "count": cnt, "n": d["citing"]})
    df = pd.DataFrame(rows)
    order = df[df.side == "deny"].sort_values("share", ascending=False).feature.tolist()
    lim = math.ceil((df.share.max() + 0.08) / 0.1) * 0.1
    ticks = [round(v, 1) for v in (-0.8, -0.6, -0.4, -0.2, 0, 0.2, 0.4, 0.6, 0.8) if abs(v) <= lim]
    color = alt.Color("side:N", scale=alt.Scale(domain=list(SIDE_COLORS), range=list(SIDE_COLORS.values())),
                      legend=alt.Legend(title=None, labelExpr=json.dumps(SIDE_LABELS) + "[datum.label]", orient="top", direction="vertical", labelLimit=400))
    tip = [alt.Tooltip("feature:N", title="Feature"), alt.Tooltip("side:N", title="Side"), alt.Tooltip("count:Q", title="Posts"), alt.Tooltip("share:Q", format=".0%", title="Share"), alt.Tooltip("n:Q", title="Posts on the side citing a feature")]
    bars = alt.Chart(df).mark_bar(height=16).encode(
        y=alt.Y("feature:N", sort=order, title=None, axis=alt.Axis(labelLimit=260)),
        x=alt.X("x:Q", title="Share of the side's feature-citing posts that point to the feature",
                axis=alt.Axis(format="%", values=ticks, labelExpr="format(abs(datum.value), '.0%')", grid=True), scale=alt.Scale(domain=[-lim, lim])),
        color=color, tooltip=tip)
    zero = alt.Chart(df).mark_rule(color=T.AXIS, strokeWidth=1).encode(x=alt.datum(0))
    lab_l = alt.Chart(df).transform_filter(alt.datum.side == "deny").mark_text(align="right", dx=-5, fontSize=11, color=T.INK2).encode(
        y=alt.Y("feature:N", sort=order), x="x:Q", text=alt.Text("share:Q", format=".0%"))
    lab_r = alt.Chart(df).transform_filter(alt.datum.side == "affirm").mark_text(align="left", dx=5, fontSize=11, color=T.INK2).encode(
        y=alt.Y("feature:N", sort=order), x="x:Q", text=alt.Text("share:Q", format=".0%"))
    profile = alt.layer(bars, zero, lab_l, lab_r).properties(width=WIDTH, height=24 * len(order))
    na, nd = S["affirm"], S["deny"]
    chart = profile.properties(title=alt.Title(
        "Where each side finds its evidence",
        subtitle=[f"Posts that commit to a side across the six questions: {nd['n']:,} deny, {na['n']:,} affirm. Of those citing at least one feature in their own direction",
                  f"({nd['citing']:,} and {na['citing']:,}), the share citing each feature, sorted by the denying side."]))
    save(chart, "features_sides")


# ---------------------------------------------------------------- composition over time

def stance_over_time():
    st = load("stance")
    events = json.loads(json.dumps(__import__("yaml").safe_load((ROOT / "config" / "events.yaml").read_text())))["events"]
    rows = []
    for q, table in st["by_quarter_unbiased"].items():
        c = table["current_conscious"]
        n = sum(c[k] for k in ("denies", "agnostic", "discusses", "asserts"))
        if n < 15:
            continue
        for k in ("denies", "agnostic", "discusses", "asserts"):
            rows.append({"quarter": q, "option": k, "share": c[k] / n, "count": c[k], "n": n})
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["quarter"].str[:4] + "-" + ((df["quarter"].str[5].astype(int) - 1) * 3 + 2).astype(str).str.zfill(2) + "-15")
    order = ["denies", "agnostic", "discusses", "asserts"]
    area = alt.Chart(df).mark_area(interpolate="monotone", opacity=0.85, stroke=T.SURFACE, strokeWidth=1.5).encode(
        x=alt.X("date:T", title=None, axis=alt.Axis(format="%b %Y", grid=False, labelAngle=0, labelPadding=18)),
        y=alt.Y("share:Q", stack="normalize", title="Share of posts addressing the claim", axis=alt.Axis(format="%", grid=True)),
        color=alt.Color("option:N", scale=alt.Scale(domain=order, range=[T.STANCE_COLORS[k] for k in order]), sort=order,
                        legend=alt.Legend(title="Current LLMs are conscious", labelExpr=json.dumps(T.STANCE_LABELS) + "[datum.label]")),
        order=alt.Order("option:N", sort="ascending"),
        tooltip=[alt.Tooltip("quarter:N", title="Quarter"), alt.Tooltip("option:N", title="Position"), alt.Tooltip("count:Q", title="Posts"), alt.Tooltip("share:Q", format=".0%", title="Share"), alt.Tooltip("n:Q", title="Posts addressing")])
    ev = pd.DataFrame(events)
    ev["date"] = pd.to_datetime(ev["date"])
    ev = ev[(ev.date >= df.date.min()) & (ev.date <= df.date.max() + pd.Timedelta(days=45))]
    rules = alt.Chart(ev).mark_rule(color=T.INK, strokeWidth=1, opacity=0.5).encode(x="date:T")
    txt = alt.Chart(ev).mark_text(align="left", dx=5, fontSize=10, color=T.INK, baseline="top").encode(x="date:T", y=alt.value(6), text="short:N")
    quarters = df.drop_duplicates("quarter")[["date", "quarter", "n"]]
    n_txt = alt.Chart(quarters).mark_text(fontSize=10, color=T.MUTED, baseline="top").encode(x="date:T", y=alt.value(238), text=alt.Text("n:Q", format=",d"))
    first_q, last_q = quarters.quarter.min(), quarters.quarter.max()
    chart = alt.layer(area, rules, txt, n_txt).properties(width=WIDTH, height=230, title=alt.Title("Stance over time, on current LLM consciousness",
                      subtitle=[f"Quarterly composition, {first_q} to {last_q}, among the {st['n_unbiased']:,} relevant posts found through web search or citation.",
                                "Substack's own search is recency-skewed and excluded; quarters with fewer than 15 posts are omitted. Grey figures: posts per quarter."]))
    save(chart, "stance_over_time")


# ---------------------------------------------------------------- top cited works

def top_cited():
    src = load("sources")
    rows = []
    for w in src["top_works"]:
        if w["tier"] in ("social",) or not (w["title"] or "").strip() or w["title"].startswith("http"):
            continue
        rows.append({"work": w["title"][:70] + ("…" if len(w["title"]) > 70 else ""), "pubs": w["citing_pubs"], "posts": w["citing_posts"],
                     "tier": w["tier"] if w["tier"] in ("academic", "lab", "substack", "press") else "other"})
        if len(rows) >= 20:
            break
    df = pd.DataFrame(rows)
    order = df.sort_values("pubs", ascending=False)["work"].tolist()
    bars = alt.Chart(df).mark_bar(height=16).encode(
        y=alt.Y("work:N", sort=order, title=None, axis=alt.Axis(labelLimit=330)),
        x=alt.X("pubs:Q", title="Publications citing the work", axis=alt.Axis(grid=True)),
        color=alt.Color("tier:N", scale=alt.Scale(domain=list(T.TIER_COLORS), range=list(T.TIER_COLORS.values())), legend=alt.Legend(title="Source", labelExpr=json.dumps(T.TIER_LABELS) + "[datum.label]")),
        tooltip=[alt.Tooltip("work:N", title="Work"), alt.Tooltip("tier:N", title="Source"), alt.Tooltip("pubs:Q", title="Citing publications"), alt.Tooltip("posts:Q", title="Citing posts")])
    labels = alt.Chart(df).mark_text(align="left", dx=5, fontSize=11, color=T.INK2).encode(y=alt.Y("work:N", sort=order), x="pubs:Q", text="pubs:Q")
    chart = alt.layer(bars, labels).properties(width=WIDTH - 160, height=20 * len(df), title=alt.Title("What the discourse cites", subtitle="Most-cited works across relevant posts, by distinct citing publications. Social media and image links excluded."))
    save(chart, "top_cited_works")


# ---------------------------------------------------------------- who writes

def who_writes():
    s = load("summary")
    df = pd.DataFrame([{"group": T.GROUP_LABELS[g], "key": g, "posts": n} for g, n in s["by_group"].items()]).sort_values("posts", ascending=False)
    bars = alt.Chart(df).mark_bar(height=20).encode(
        y=alt.Y("group:N", sort=df["group"].tolist(), title=None),
        x=alt.X("posts:Q", title="Relevant posts", axis=alt.Axis(grid=True)),
        color=alt.Color("key:N", scale=alt.Scale(domain=list(T.GROUP_COLORS), range=list(T.GROUP_COLORS.values())), legend=None),
        tooltip=[alt.Tooltip("group:N", title="Publication type"), alt.Tooltip("posts:Q", title="Posts")])
    labels = alt.Chart(df).mark_text(align="left", dx=5, fontSize=11, color=T.INK2).encode(y=alt.Y("group:N", sort=df["group"].tolist()), x="posts:Q", text=alt.Text("posts:Q", format=",d"))
    chart = alt.layer(bars, labels).properties(width=WIDTH - 60, height=24 * len(df), title=alt.Title("Who writes about machine minds", subtitle="Relevant posts by publication type."))
    save(chart, "who_writes")


# ---------------------------------------------------------------- named people

def people():
    src = load("sources")
    df = pd.DataFrame(src["people"][:18])
    order = df["name"].tolist()
    tooltip = [alt.Tooltip("name:N"), alt.Tooltip("group:N", title="Role"), alt.Tooltip("posts:Q", title="Posts"), alt.Tooltip("share:Q", format=".0%", title="Share")]
    # Names are drawn as a text layer (not axis labels) so each can carry a link to the person's Wikipedia article.
    # People without one (`url` null) get separate layers with no href: a null href still renders as a broken anchor.
    linked, plain = alt.Chart(df).transform_filter("isValid(datum.url)"), alt.Chart(df).transform_filter("!isValid(datum.url)")
    y = alt.Y("name:N", sort=order, title=None, axis=alt.Axis(labelColor="transparent", labelPadding=8))   # invisible labels reserve the margin
    x = alt.X("posts:Q", title="Relevant posts mentioning the name", axis=alt.Axis(grid=True))
    bars = alt.layer(linked.mark_bar(height=14, color=T.BLUE).encode(y=y, x=x, href="url:N", tooltip=tooltip),
                     plain.mark_bar(height=14, color=T.BLUE).encode(y=y, x=x, tooltip=tooltip))
    names = alt.layer(linked.mark_text(align="right", dx=-8, fontSize=12, color=T.BLUE, cursor="pointer").encode(y=y, x=alt.value(0), text="name:N", href="url:N", tooltip=tooltip),
                      plain.mark_text(align="right", dx=-8, fontSize=12, color=T.INK2).encode(y=y, x=alt.value(0), text="name:N", tooltip=tooltip))
    labels = alt.Chart(df).mark_text(align="left", dx=5, fontSize=11, color=T.INK2).encode(y=alt.Y("name:N", sort=order), x="posts:Q", text=alt.Text("posts:Q", format=",d"))
    chart = alt.layer(bars, names, labels).properties(width=WIDTH - 120, height=18 * len(df),
                                                      title=alt.Title("Who gets named", subtitle="People mentioned by name in relevant posts. Names link to Wikipedia."))
    save(chart, "people_named")


# ---------------------------------------------------------------- topics

def topics():
    tp = load("topics")
    df = pd.DataFrame([{"label": t["label"], "size": t["size"], "core": t["core_size"] or 0, "denies": t["stance_current_conscious"].get("denies", 0), "asserts": t["stance_current_conscious"].get("asserts", 0)} for t in tp[:20]])
    order = df["label"].tolist()
    bars = alt.Chart(df).mark_bar(height=14, color=T.BLUE).encode(
        y=alt.Y("label:N", sort=order, title=None, axis=alt.Axis(labelLimit=300)), x=alt.X("size:Q", title="Posts in cluster", axis=alt.Axis(grid=True)),
        tooltip=[alt.Tooltip("label:N", title="Topic"), alt.Tooltip("size:Q", title="Posts"), alt.Tooltip("core:Q", title="Core members"), alt.Tooltip("asserts:Q", title="Assert consciousness"), alt.Tooltip("denies:Q", title="Deny consciousness")])
    labels = alt.Chart(df).mark_text(align="left", dx=5, fontSize=11, color=T.INK2).encode(y=alt.Y("label:N", sort=order), x="size:Q", text=alt.Text("size:Q", format=",d"))
    chart = alt.layer(bars, labels).properties(width=WIDTH - 180, height=18 * len(df), title=alt.Title("The twenty largest topics", subtitle="Clusters of relevant posts by embedding similarity, with hand-checked labels."))
    save(chart, "topics_top")


ALL = {"stance_landscape": stance_landscape, "stance_by_group": stance_by_group, "arguments_frequency": arguments_frequency, "stance_over_time": stance_over_time,
       "axes_landscape": axes_landscape, "axes_by_group": axes_by_group, "axes_over_time": axes_over_time, "axes_profile": axes_profile, "axes_profile_agency": axes_profile_agency,
       "top_cited_works": top_cited, "who_writes": who_writes, "people_named": people, "topics_top": topics,
       "features_landscape": features_landscape, "features_over_time": features_over_time, "features_sides": features_sides}

if __name__ == "__main__":
    names = sys.argv[1:] or list(ALL)
    for n in names:
        ALL[n]()
