// Shared chart helpers for the site. Colours come from the CSS tokens in style.css so light and dark
// modes stay consistent with the static figures (same slots, dark steps selected for the dark surface).
import * as Plot from "npm:@observablehq/plot";
import embed from "npm:vega-embed";

export const STANCE_OPTIONS = ["denies", "agnostic", "discusses", "asserts"];
export const STANCE_LABELS = {denies: "Denies", agnostic: "Agnostic", discusses: "Discusses, no position", asserts: "Asserts", reports_only: "Reports others only", not_addressed: "Not addressed"};
export const GROUP_LABELS = {general: "General and culture", ai_field: "AI field", academic: "Academic", journalism: "Journalism and politics", religion: "Religion and spirituality"};
export const GROUP_ORDER = ["general", "ai_field", "academic", "journalism", "religion"];
export const GENRE_LABELS = {essay: "Essay", roundup: "Roundup", fiction: "Fiction", transcript: "Model transcript", interview_podcast: "Interview or podcast", other: "Other"};
export const ITEM_LABELS = {
  current_conscious: "Current LLMs are conscious", potential_conscious: "AI could be conscious in principle",
  current_cognition: "Current LLMs genuinely think", potential_cognition: "AI could genuinely think",
  understanding: "LLMs genuinely understand", beliefs_knowledge: "LLMs have beliefs or knowledge",
  emotions: "LLMs have emotions or can suffer", agency: "LLMs have goals or agency of their own",
  moral_worth_current: "Current LLMs have moral worth", moral_worth_potential: "Future AI could have moral worth",
  advance_needed: "Current architectures are insufficient", cannot_know: "We cannot know whether AI is conscious",
  precaution: "Act with precaution regardless", deflationary: "AI consciousness talk is hype"
};
// Derived axes (mcreview.axes): five positions computed from the stance items; the site's headline view.
export const AXIS_KEYS = ["experience_now", "cognition_now", "agency_now", "possible", "moral_status", "serious"];
export const AXIS_LABELS = {
  experience_now: "Current LLMs have experience", cognition_now: "Current LLMs genuinely think", agency_now: "Current LLMs have goals of their own",
  possible: "AI could have a mind in principle", moral_status: "AI has moral status", serious: "AI consciousness is a serious question"
};
export const AXIS_QUALIFIED = {
  cognition_now: "Partly: yes on some capacities, no on others", possible: "Yes, but only after a major advance beyond current architectures",
  moral_status: "Not now, but future AI could, or act with precaution regardless"
};
export const LEVELS = ["no", "unsure", "discussed", "yes_qualified", "yes"];   // left to right on the diverging bar
export const LEVEL_LABELS = {no: "No", unsure: "Unsure", discussed: "Discussed, no position", yes_qualified: "Yes, qualified", yes: "Yes", not_addressed: "Not addressed"};
export const ARG_LABELS = {
  arg_chinese_room: "Chinese room", arg_stochastic_parrot: "Stochastic parrot / next-token", arg_hard_problem: "Hard problem",
  arg_other_minds: "Other minds / behavioural evidence", arg_self_report: "Self-reports unreliable", arg_functionalism: "Functionalism / substrate independence",
  arg_biological: "Biology or embodiment required", arg_theory_indicators: "Theory-based indicators", arg_emergence: "Emergence from scale",
  arg_anthropomorphism: "Anthropomorphism warning", arg_precaution_moral_circle: "Precaution / moral circle", arg_mimicry: "Mimicry of training data",
  arg_panpsychism_illusionism: "Panpsychism or illusionism"
};

export function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}
export function stanceColors() {
  return {denies: cssVar("--stance-denies"), agnostic: cssVar("--stance-agnostic"), discusses: cssVar("--stance-discusses"), asserts: cssVar("--stance-asserts")};
}
export function axisColors() {
  return {no: cssVar("--axis-no"), unsure: cssVar("--axis-unsure"), discussed: cssVar("--axis-discussed"), yes_qualified: cssVar("--axis-yes-qualified"), yes: cssVar("--axis-yes")};
}
export function groupColors() {
  return {general: cssVar("--series-1"), ai_field: cssVar("--series-2"), academic: cssVar("--series-3"), journalism: cssVar("--series-4"), religion: cssVar("--series-5")};
}

// Render a Vega-Lite spec exported by analysis/figures/make.py, re-themed for the current surface.
export async function vlChart(spec, {width} = {}) {
  const fg = cssVar("--theme-foreground") || "#0b0b0b";
  const muted = cssVar("--theme-foreground-muted") || "#898781";
  const grid = cssVar("--grid") || "#e1e0d9";
  const s = structuredClone(spec);
  s.background = "transparent";
  s.config = s.config || {};
  Object.assign(s.config, {
    title: {...(s.config.title || {}), color: fg, subtitleColor: muted},
    axis: {...(s.config.axis || {}), labelColor: muted, titleColor: muted, gridColor: grid, domainColor: grid, tickColor: grid},
    legend: {...(s.config.legend || {}), labelColor: fg, titleColor: muted},
    header: {...(s.config.header || {}), labelColor: fg, titleColor: muted},
    text: {...(s.config.text || {}), color: fg}
  });
  if (width) s.width = Math.max(320, width);
  const el = document.createElement("div");
  el.className = "vl";
  // href-encoded marks (names in the people chart) open in a new tab, like the site's other external links.
  await embed(el, s, {actions: false, renderer: "svg", loader: {target: "_blank", rel: "noopener"}});
  return el;
}

// Diverging stacked bar (Likert) of stance shares, from a table {item: {option: count}}.
export function stanceDiverging(table, {items = Object.keys(ITEM_LABELS), width = 640, title} = {}) {
  const colors = stanceColors();
  const rows = [];
  for (const item of items) {
    const c = table[item];
    if (!c) continue;
    const n = STANCE_OPTIONS.reduce((a, k) => a + (c[k] || 0), 0);
    if (!n) continue;
    const sh = Object.fromEntries(STANCE_OPTIONS.map((k) => [k, (c[k] || 0) / n]));
    let x = -(sh.denies + (sh.agnostic + sh.discusses) / 2);
    for (const k of STANCE_OPTIONS) {
      rows.push({item: ITEM_LABELS[item] || item, key: item, option: k, x1: x, x2: x + sh[k], share: sh[k], count: c[k] || 0, n, asserts: sh.asserts, denies: sh.denies});
      x += sh[k];
    }
  }
  const order = [...new Set(rows.filter((r) => r.option === "asserts").sort((a, b) => b.asserts - a.asserts).map((r) => r.item))];
  return Plot.plot({
    title, width, height: 30 * order.length + 60, marginLeft: 250, marginRight: 90,
    x: {label: "Share of posts addressing the claim", domain: [-1, 1], tickFormat: (d) => `${Math.round(Math.abs(d) * 100)}%`, grid: true},
    y: {domain: order, label: null},
    color: {domain: STANCE_OPTIONS, range: STANCE_OPTIONS.map((k) => colors[k]), legend: true, tickFormat: (d) => STANCE_LABELS[d]},
    marks: [
      Plot.barX(rows, {x1: "x1", x2: "x2", y: "item", fill: "option", insetTop: 4, insetBottom: 4, stroke: "var(--theme-background)", strokeWidth: 2,
        title: (d) => `${d.item}\n${STANCE_LABELS[d.option]}: ${d.count} posts (${Math.round(d.share * 100)}%) of ${d.n} addressing`}),
      Plot.ruleX([0], {stroke: "var(--axis)"}),
      // percent labels only where there is a bar to label; a full-width bar gets its label inside
      Plot.text(rows.filter((r) => r.option === "asserts" && r.asserts > 0 && r.asserts < 0.9), {x: "x2", y: "item", text: (d) => `${Math.round(d.asserts * 100)}%`, dx: 6, textAnchor: "start", fill: "var(--theme-foreground-muted)", fontSize: 11}),
      Plot.text(rows.filter((r) => r.option === "asserts" && r.asserts >= 0.9), {x: "x2", y: "item", text: (d) => `${Math.round(d.asserts * 100)}%`, dx: -6, textAnchor: "end", fill: "white", fontSize: 11}),
      Plot.text(rows.filter((r) => r.option === "denies" && r.denies > 0 && r.denies < 0.9), {x: "x1", y: "item", text: (d) => `${Math.round(d.denies * 100)}%`, dx: -6, textAnchor: "end", fill: "var(--theme-foreground-muted)", fontSize: 11}),
      Plot.text(rows.filter((r) => r.option === "denies" && r.denies >= 0.9), {x: "x1", y: "item", text: (d) => `${Math.round(d.denies * 100)}%`, dx: 6, textAnchor: "start", fill: "white", fontSize: 11}),
      Plot.text(rows.filter((r) => r.option === "asserts"), {x: 1, y: "item", text: (d) => d.n.toLocaleString(), dx: 40, textAnchor: "start", fill: "var(--theme-foreground-muted)", fontSize: 10})
    ]
  });
}

// Diverging stacked bar of the derived axes, from a table {axis: {level: count}}. Yes and qualified yes on the
// right, no on the left, unsure and discussed straddling zero. Shares are of posts addressing the axis.
export function axesDiverging(table, {axes = AXIS_KEYS, width = 640, title} = {}) {
  const colors = axisColors();
  const rows = [];
  for (const axis of axes) {
    const c = table[axis];
    if (!c) continue;
    const n = LEVELS.reduce((a, k) => a + (c[k] || 0), 0);
    if (!n) continue;
    const sh = Object.fromEntries(LEVELS.map((k) => [k, (c[k] || 0) / n]));
    const pos = sh.yes + sh.yes_qualified;
    let x = -(sh.no + (sh.unsure + sh.discussed) / 2);
    for (const k of LEVELS) {
      rows.push({item: AXIS_LABELS[axis] || axis, key: axis, option: k, x1: x, x2: x + sh[k], share: sh[k], count: c[k] || 0, n, pos, neg: sh.no});
      x += sh[k];
    }
  }
  const order = [...new Set(rows.filter((r) => r.option === "yes").sort((a, b) => b.pos - a.pos).map((r) => r.item))];
  const label = (d) => d.option === "yes_qualified" && AXIS_QUALIFIED[d.key] ? `${LEVEL_LABELS[d.option]} (${AXIS_QUALIFIED[d.key]})` : LEVEL_LABELS[d.option];
  return Plot.plot({
    title, width, height: 32 * order.length + 60, marginLeft: 250, marginRight: 90,
    x: {label: "Share of posts addressing the question", domain: [-1, 1], tickFormat: (d) => `${Math.round(Math.abs(d) * 100)}%`, grid: true},
    y: {domain: order, label: null},
    color: {domain: LEVELS, range: LEVELS.map((k) => colors[k]), legend: true, tickFormat: (d) => LEVEL_LABELS[d]},
    marks: [
      Plot.barX(rows, {x1: "x1", x2: "x2", y: "item", fill: "option", insetTop: 4, insetBottom: 4, stroke: "var(--theme-background)", strokeWidth: 2,
        title: (d) => `${d.item}\n${label(d)}: ${d.count} posts (${Math.round(d.share * 100)}%) of ${d.n} addressing`}),
      Plot.ruleX([0], {stroke: "var(--axis)"}),
      Plot.text(rows.filter((r) => r.option === "yes" && r.pos > 0 && r.pos < 0.9), {x: "x2", y: "item", text: (d) => `${Math.round(d.pos * 100)}%`, dx: 6, textAnchor: "start", fill: "var(--theme-foreground-muted)", fontSize: 11}),
      Plot.text(rows.filter((r) => r.option === "yes" && r.pos >= 0.9), {x: "x2", y: "item", text: (d) => `${Math.round(d.pos * 100)}%`, dx: -6, textAnchor: "end", fill: "white", fontSize: 11}),
      Plot.text(rows.filter((r) => r.option === "no" && r.neg > 0 && r.neg < 0.9), {x: "x1", y: "item", text: (d) => `${Math.round(d.neg * 100)}%`, dx: -6, textAnchor: "end", fill: "var(--theme-foreground-muted)", fontSize: 11}),
      Plot.text(rows.filter((r) => r.option === "no" && r.neg >= 0.9), {x: "x1", y: "item", text: (d) => `${Math.round(d.neg * 100)}%`, dx: 6, textAnchor: "start", fill: "white", fontSize: 11}),
      Plot.text(rows.filter((r) => r.option === "yes"), {x: 1, y: "item", text: (d) => d.n.toLocaleString(), dx: 40, textAnchor: "start", fill: "var(--theme-foreground-muted)", fontSize: 10})
    ]
  });
}

// Count posts per level for each axis, from a list of post objects.
export function axesTable(posts, axes = AXIS_KEYS) {
  const t = {};
  for (const a of axes) {
    t[a] = {};
    for (const p of posts) {
      const v = p.axes?.[a];
      if (v) t[a][v] = (t[a][v] || 0) + 1;
    }
  }
  return t;
}

// Count posts per stance option for each item, from a list of post objects.
export function stanceTable(posts, items = Object.keys(ITEM_LABELS)) {
  const t = {};
  for (const it of items) {
    t[it] = {};
    for (const p of posts) {
      const v = p.stance?.[it];
      if (v) t[it][v] = (t[it][v] || 0) + 1;
    }
  }
  return t;
}

export function stat(label, value, note) {
  const el = document.createElement("div");
  el.className = "stat";
  const cls = String(value).length > 14 ? "value value-text" : "value";
  el.innerHTML = `<div class="label">${label}</div><div class="${cls}">${value}</div>${note ? `<div class="sub">${note}</div>` : ""}`;
  return el;
}

export function statRow(items) {
  const row = document.createElement("div");
  row.className = "stat-row";
  for (const [l, v, n] of items) row.appendChild(stat(l, v, n));
  return row;
}

export function postLink(p) {
  return `<a href="${p.url}" target="_blank" rel="noopener">${escapeHtml(p.title || "(untitled)")}</a>`;
}
export function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"]/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
}
export const fmtDate = (d) => (d ? d.slice(0, 10) : "");
