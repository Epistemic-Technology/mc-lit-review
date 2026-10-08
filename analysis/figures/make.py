"""Static figures for the post, from the exported data (site/src/data). Writes PNG (1200 px wide, 2x) and
SVG to figures/, and the Vega-Lite spec to site/src/charts/ so the site can render the same chart live.

Run: uv run python analysis/figures/make.py [name ...]
"""
from __future__ import annotations

import json
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
    df = pd.DataFrame(rows)
    order = (df[df.option == sc["pos"]].groupby("item")["asserts_share"].mean().sort_values(ascending=False).index.tolist())
    # In facet mode every layer must be data-less so the facet partition applies; the data goes on the facet.
    src = alt.Chart(df) if facet_col is None else alt.Chart()
    base = src.encode(
        y=alt.Y("item:N", sort=order, title=None, axis=alt.Axis(labelLimit=260)),
    )
    bars = base.mark_bar(height=18, cornerRadiusEnd=0).encode(
        x=alt.X("x0:Q", title=sc["x_title"], axis=alt.Axis(format="%", values=[-1, -0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75, 1], labelExpr="abs(datum.value) == 1 ? format(abs(datum.value), '.0%') : format(abs(datum.value), '.0%')", grid=True), scale=alt.Scale(domain=[-1, 1])),
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


def axes_over_time():
    """Composition by quarter for the two 'now' axes, on the recency-unbiased channels."""
    st, axes = _axes_meta()
    events = __import__("yaml").safe_load((ROOT / "config" / "events.yaml").read_text())["events"]
    keys = ["no", "unsure", "discussed", "yes_qualified", "yes"]
    label_of = {a["name"]: a["label"] for a in axes}
    axes_shown = ("experience_now", "cognition_now", "agency_now")
    # Start at the first quarter from which every shown axis stays at or above the threshold, so the series is
    # unbroken: an omitted quarter in the middle would make the area interpolate across a gap.
    qs = sorted(st["by_quarter_unbiased"])
    ok = [all(sum(st["by_quarter_unbiased"][q][ax][k] for k in keys) >= 15 for ax in axes_shown) for q in qs]
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
    ev = pd.DataFrame(events)
    ev["date"] = pd.to_datetime(ev["date"])
    ev = ev[(ev.date >= df.date.min()) & (ev.date <= df.date.max() + pd.Timedelta(days=45))].reset_index(drop=True)
    ev["ty"] = 6 + 14 * (ev.index % 2)   # stagger neighbouring labels
    ev["late"] = ev.date > df.date.min() + 0.8 * (df.date.max() - df.date.min())   # right-align labels near the end
    area = alt.Chart().mark_area(interpolate="monotone", opacity=0.85, stroke=T.SURFACE, strokeWidth=1.5).encode(
        x=alt.X("date:T", title=None, axis=alt.Axis(format="%b %Y", grid=False, labelAngle=0, labelPadding=18)),
        y=alt.Y("share:Q", stack="normalize", title="Share of posts", axis=alt.Axis(format="%", grid=True)),
        color=alt.Color("option:N", scale=alt.Scale(domain=keys, range=[T.AXIS_COLORS[k] for k in keys]), sort=keys,
                        legend=alt.Legend(title="Author's position", labelExpr=json.dumps(T.AXIS_LABELS) + "[datum.label]")),
        order=alt.Order("option:N", sort="ascending"),
        tooltip=[alt.Tooltip("axis:N", title="Question"), alt.Tooltip("quarter:N", title="Quarter"), alt.Tooltip("option:N", title="Position"), alt.Tooltip("count:Q", title="Posts"), alt.Tooltip("share:Q", format=".0%", title="Share"), alt.Tooltip("n:Q", title="Posts addressing")])
    rules = alt.Chart(ev).mark_rule(color=T.INK, strokeWidth=1, opacity=0.5).encode(x="date:T")
    txt = [alt.Chart(ev[(ev.ty == v) & (ev.late == late)]).mark_text(align="right" if late else "left", dx=-5 if late else 5, fontSize=10, color=T.INK, baseline="top").encode(x="date:T", y=alt.value(v), text="short:N")
           for v in sorted(ev.ty.unique()) for late in (False, True) if len(ev[(ev.ty == v) & (ev.late == late)])]
    first_q, last_q = df.quarter.min(), df.quarter.max()
    chart = alt.layer(area, rules, *txt, data=df).properties(width=WIDTH, height=170).facet(
        row=alt.Row("axis:N", title=None, sort=[label_of[a] for a in axes_shown], header=alt.Header(labelAngle=0, labelAlign="left", labelOrient="top")),
        title=alt.Title("Positions over time", subtitle=[f"Quarterly composition, {first_q} to {last_q}, among the {st['n_unbiased']:,} relevant posts found through web search or citation.",
                                                         "Substack's own search is recency-skewed and excluded; quarters with fewer than 15 posts are omitted."]))
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


# ---------------------------------------------------------------- arguments: frequency x traction

ARG_LABELS = {
    "arg_chinese_room": "Chinese room", "arg_stochastic_parrot": "Stochastic parrot / next-token", "arg_hard_problem": "Hard problem",
    "arg_other_minds": "Other minds / behavioural evidence", "arg_self_report": "Self-reports unreliable", "arg_functionalism": "Functionalism / substrate independence",
    "arg_biological": "Biology or embodiment required", "arg_theory_indicators": "Theory-based indicators", "arg_emergence": "Emergence from scale",
    "arg_anthropomorphism": "Anthropomorphism warning", "arg_precaution_moral_circle": "Precaution / moral circle", "arg_mimicry": "Mimicry of training data",
    "arg_panpsychism_illusionism": "Panpsychism or illusionism",
}


def arguments_scatter():
    """Two aligned panels on one argument order: how often each argument appears, and how posts using it
    perform against their publication's baseline. Two measures of different scale -> two charts, one axis each."""
    args = load("arguments")
    df = pd.DataFrame([{"label": ARG_LABELS.get(a["name"], a["name"]), "share": a["share"], "traction": a["median_over_performance"] or 0, "n": a["n"], "cited": a["share_cited"]} for a in args])
    order = df.sort_values("share", ascending=False)["label"].tolist()
    tips = [alt.Tooltip("label:N", title="Argument"), alt.Tooltip("n:Q", title="Posts"), alt.Tooltip("share:Q", format=".0%", title="Share"), alt.Tooltip("traction:Q", format=".2f", title="Median over-performance"), alt.Tooltip("cited:Q", format=".0%", title="Share cited by another publication")]
    y = alt.Y("label:N", sort=order, title=None, axis=alt.Axis(labelLimit=280))
    freq = alt.Chart(df).mark_bar(height=14, color=T.BLUE).encode(y=y, x=alt.X("share:Q", title="Share of relevant posts", axis=alt.Axis(format="%", grid=True, tickCount=4)), tooltip=tips)
    freq_lab = alt.Chart(df).mark_text(align="left", dx=5, fontSize=11, color=T.INK2).encode(y=y, x="share:Q", text=alt.Text("share:Q", format=".0%"))
    left = alt.layer(freq, freq_lab).properties(width=250, height=18 * len(df), title=alt.Title("How often it appears", fontSize=13, fontWeight=600, color=T.INK2))
    ref = alt.Chart(pd.DataFrame({"x": [1.0]})).mark_rule(color=T.AXIS, strokeWidth=1).encode(x="x:Q")
    dots = alt.Chart(df).mark_point(size=80, color=T.BLUE, stroke=T.SURFACE, strokeWidth=2).encode(
        y=alt.Y("label:N", sort=order, title=None, axis=None), x=alt.X("traction:Q", title="Median reactions vs the publication's typical post", axis=alt.Axis(grid=True, format=".2f", tickCount=4), scale=alt.Scale(domain=[0.7, 1.1], zero=False)), tooltip=tips)
    dot_lab = alt.Chart(df).mark_text(align="left", dx=9, fontSize=11, color=T.INK2).encode(y=alt.Y("label:N", sort=order, axis=None), x="traction:Q", text=alt.Text("traction:Q", format=".2f"))
    ref_txt = alt.Chart(pd.DataFrame({"x": [1.0]})).mark_text(align="left", dx=4, fontSize=10, color=T.MUTED, baseline="top").encode(x="x:Q", y=alt.value(-2), text=alt.value("typical post = 1.0"))
    right = alt.layer(ref, dots, dot_lab, ref_txt).properties(width=220, height=18 * len(df), title=alt.Title("How it performs", fontSize=13, fontWeight=600, color=T.INK2))
    chart = alt.hconcat(left, right, spacing=24).properties(title=alt.Title("Which arguments are common, and which get traction",
                        subtitle="Argument types coded per post. Right: median reactions of posts using the argument, relative to each publication's own posts in the period (1.0 = a typical post)."))
    chart = chart.configure_concat(spacing=24)
    save(chart, "arguments_traction")


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
    bars = alt.Chart(df).mark_bar(height=14, color=T.BLUE).encode(
        y=alt.Y("name:N", sort=order, title=None), x=alt.X("posts:Q", title="Relevant posts mentioning the name", axis=alt.Axis(grid=True)),
        tooltip=[alt.Tooltip("name:N"), alt.Tooltip("group:N", title="Role"), alt.Tooltip("posts:Q", title="Posts"), alt.Tooltip("share:Q", format=".0%", title="Share")])
    labels = alt.Chart(df).mark_text(align="left", dx=5, fontSize=11, color=T.INK2).encode(y=alt.Y("name:N", sort=order), x="posts:Q", text=alt.Text("posts:Q", format=",d"))
    chart = alt.layer(bars, labels).properties(width=WIDTH - 120, height=18 * len(df), title=alt.Title("Who gets named", subtitle="People mentioned by name in relevant posts."))
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


ALL = {"stance_landscape": stance_landscape, "stance_by_group": stance_by_group, "arguments_traction": arguments_scatter, "stance_over_time": stance_over_time,
       "axes_landscape": axes_landscape, "axes_by_group": axes_by_group, "axes_over_time": axes_over_time, "axes_profile": axes_profile, "axes_profile_agency": axes_profile_agency,
       "top_cited_works": top_cited, "who_writes": who_writes, "people_named": people, "topics_top": topics}

if __name__ == "__main__":
    names = sys.argv[1:] or list(ALL)
    for n in names:
        ALL[n]()
