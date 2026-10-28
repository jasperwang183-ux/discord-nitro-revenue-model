// Nitro revenue model site. Charts are plain SVG; the model itself is src/nitro_model/cohorts.py run by Pyodide.
const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.27.2/full/";
const LAYER_COLORS = {
  "Opening book": "var(--opening)", "Signed up 2025": "var(--c2025)", "Signed up 2026": "var(--c2026)",
  "Signed up 2027": "var(--c2027)", "Signed up 2028-30": "var(--c2028)", "Reactivated": "var(--react)",
  "In free trial": "var(--trial)",
};
const PCT_KEYS = new Set(["churn_m1", "churn_tail", "annual_renewal_first", "trial_share", "trial_to_paid", "react_rate", "mau_growth_first"]);

const REGION_LABEL = { US_CA: "US & Canada", EUROPE: "Europe", LATAM: "Latin America", APAC: "Asia-Pacific", ROW: "Rest of world" };
const PLAN_LABEL = { NITRO_M: "Nitro monthly", NITRO_A: "Nitro annual", BASIC_M: "Basic monthly", BASIC_A: "Basic annual" };
const WALK_SHORT = { "US list price": "US list", "Regional pricing": "Regional", "Discounts": "Discounts", "VAT": "VAT",
  "App store & card fees": "Store fees", "FX": "FX" };
let walkYear = 0;
const state = { base: null, params0: null, sliders: [], current: null, params: null, py: null, busy: false, queued: false };
const $ = (id) => document.getElementById(id);

// ---------- formatting ----------
const fmtM = (v, d = 2) => (v / 1e6).toFixed(d) + "M";
const fmtUSD = (v) => "$" + Math.round(v / 1e6).toLocaleString() + "M";
const fmtVal = (key, v) => PCT_KEYS.has(key) ? (v * 100).toFixed(v < 0.1 ? 1 : 0) + "%" : v.toFixed(2) + "x";
const signed = (v, f) => (v >= 0 ? "+" : "−") + f(Math.abs(v));

function years(s) {
  const out = [];
  for (let y = 0; y < s.months.length / 12; y++) {
    const sl = (k) => s[k].slice(12 * y, 12 * y + 12);
    const sum = (a) => a.reduce((x, z) => x + z, 0);
    const paying = sl("paying");
    out.push({
      year: s.months[12 * y].slice(0, 4), opening: s.opening[12 * y], new: sum(sl("new")),
      reactivated: sum(sl("reactivated")), churned: sum(sl("churned")), closing: s.closing[12 * y + 11],
      revenue: sum(sl("revenue")), arpu: sum(sl("revenue")) / (sum(paying) / 12),
    });
  }
  return out;
}

// ---------- SVG helpers ----------
const NS = "http://www.w3.org/2000/svg";
function el(tag, attrs = {}, parent) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}
// Round tick step (1, 2, 2.5 or 5 x 10^k) giving at most 5 intervals; returns [max, step].
function niceScale(v) {
  const raw = v / 5, p = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * p).find((s) => s >= raw);
  return [Math.ceil(v / step) * step, step];
}
function gridlines(svg, y, max, step, x1, x2, label) {
  for (let v = 0; v <= max + step / 2; v += step) {
    el("line", { x1, x2, y1: y(v), y2: y(v), stroke: v ? "var(--grid)" : "var(--axis)", "stroke-width": 1 }, svg);
    el("text", { x: x1 - 8, y: y(v) + 4, "text-anchor": "end" }, svg).textContent = label(v);
  }
}
function tooltip(container) {
  let t = container.querySelector(".tip");
  if (!t) { t = document.createElement("div"); t.className = "tip"; container.appendChild(t); }
  return t;
}
function placeTip(tip, container, x, y) {
  tip.style.display = "block";
  const w = tip.offsetWidth, cw = container.clientWidth;
  tip.style.left = Math.max(0, Math.min(cw - w, x + 12)) + "px";
  tip.style.top = Math.max(0, y - tip.offsetHeight - 8) + "px";
}

// ---------- charts ----------
function revenueChart(cur, base, changed) {
  const box = $("rev-chart");
  box.querySelectorAll("svg").forEach((s) => s.remove());
  const W = 720, H = 260, m = { l: 52, r: 8, t: 12, b: 26 };
  const ys = years(cur.summary), yb = years(base.summary);
  const [lo, hi] = cur.checks.band;
  const [max, tick] = niceScale(Math.max(...ys.map((d) => d.revenue), ...yb.map((d) => d.revenue), hi) * 1.05);
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Net revenue by year, bar chart" }, box);
  const y = (v) => m.t + (H - m.t - m.b) * (1 - v / max);
  const step = (W - m.l - m.r) / ys.length, bw = Math.min(56, step * 0.5);
  gridlines(svg, y, max, tick, m.l, W - m.r, (v) => "$" + Math.round(v / 1e6) + "M");
  // public-estimate band behind FY2025
  const bx = m.l + step * 0.5 - step * 0.45;
  el("rect", { x: bx, width: step * 0.9, y: y(hi), height: y(lo) - y(hi), fill: "var(--band)" }, svg);
  for (const v of [lo, hi]) el("line", { x1: bx, x2: bx + step * 0.9, y1: y(v), y2: y(v), stroke: "var(--series-1)", "stroke-width": 1, opacity: 0.6 }, svg);
  const tip = tooltip(box);
  ys.forEach((d, i) => {
    const cx = m.l + step * (i + 0.5);
    if (changed) {
      const b = yb[i];
      el("rect", { x: cx - bw / 2 - 3, y: y(b.revenue) - 1.5, width: bw + 6, height: y(0) - y(b.revenue) + 1.5, rx: 4,
        fill: "none", stroke: "var(--ghost)", "stroke-width": 1.5 }, svg);
    }
    el("path", { d: roundTop(cx - bw / 2, y(d.revenue), bw, y(0) - y(d.revenue), 4), fill: "var(--series-1)" }, svg);
    el("text", { x: cx, y: H - 8, "text-anchor": "middle" }, svg).textContent = "FY" + d.year;
    if (i === 0 || i === ys.length - 1) el("text", { x: cx, y: y(d.revenue) - 6, "text-anchor": "middle", style: "fill: var(--ink-2)" }, svg).textContent = fmtUSD(d.revenue);
    const hit = el("rect", { x: cx - step / 2, y: m.t, width: step, height: H - m.t - m.b, fill: "transparent" }, svg);
    hit.addEventListener("mousemove", (e) => {
      const r = box.getBoundingClientRect();
      tip.innerHTML = `<b>FY${d.year}</b><div class="r"><span>Net revenue</span><span>${fmtUSD(d.revenue)}</span></div>` +
        (changed ? `<div class="r"><span>Base case</span><span>${fmtUSD(yb[i].revenue)}</span></div>` : "") +
        `<div class="r"><span>Net $/paying sub/yr</span><span>$${d.arpu.toFixed(2)}</span></div>`;
      placeTip(tip, box, e.clientX - r.left, e.clientY - r.top);
    });
    hit.addEventListener("mouseleave", () => (tip.style.display = "none"));
  });
  const bandKey = `<span><i style="background:var(--band);border:1px solid var(--series-1)"></i>Public estimates for FY2025 ($${lo / 1e6}–${hi / 1e6}M)</span>`;
  $("rev-legend").innerHTML = (changed
    ? `<span><i style="background:var(--series-1)"></i>Your inputs</span><span><i class="outline"></i>Base case</span>`
    : `<span><i style="background:var(--series-1)"></i>Net revenue</span>`) + bandKey;
}
function roundTop(x, y, w, h, r) {
  r = Math.min(r, h, w / 2);
  return `M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h}Z`;
}

function subscriberChart(cur) {
  const box = $("sub-chart");
  box.querySelectorAll("svg").forEach((s) => s.remove());
  const W = 720, H = 280, m = { l: 44, r: 8, t: 12, b: 26 };
  const names = Object.keys(cur.layers).filter((k) => cur.layers[k].some((v) => v > 1));
  const T = cur.summary.months.length;
  const totals = cur.summary.closing;
  const [max, tick] = niceScale(Math.max(...totals) * 1.05);
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Subscribers by cohort, stacked area chart" }, box);
  const x = (t) => m.l + ((W - m.l - m.r) * t) / (T - 1);
  const y = (v) => m.t + (H - m.t - m.b) * (1 - v / max);
  gridlines(svg, y, max, tick, m.l, W - m.r, (v) => (v / 1e6).toFixed(v % 1e6 ? 1 : 0) + "M");
  for (let t = 0; t < T; t += 12) el("text", { x: x(t), y: H - 8, "text-anchor": "start" }, svg).textContent = cur.summary.months[t].slice(0, 4);
  const lower = new Array(T).fill(0);
  for (const n of names) {
    const upper = lower.map((v, t) => v + cur.layers[n][t]);
    let d = `M${x(0)},${y(upper[0])}`;
    for (let t = 1; t < T; t++) d += `L${x(t)},${y(upper[t])}`;
    for (let t = T - 1; t >= 0; t--) d += `L${x(t)},${y(lower[t])}`;
    el("path", { d: d + "Z", fill: LAYER_COLORS[n], stroke: "var(--surface)", "stroke-width": 1.5, "stroke-linejoin": "round" }, svg);
    upper.forEach((v, t) => (lower[t] = v));
  }
  const cross = el("line", { y1: m.t, y2: H - m.b, stroke: "var(--ink-2)", "stroke-width": 1, opacity: 0 }, svg);
  const tip = tooltip(box);
  const hit = el("rect", { x: m.l, y: m.t, width: W - m.l - m.r, height: H - m.t - m.b, fill: "transparent" }, svg);
  hit.addEventListener("mousemove", (e) => {
    const r = svg.getBoundingClientRect();
    const t = Math.max(0, Math.min(T - 1, Math.round(((e.clientX - r.left) * (W / r.width) - m.l) / ((W - m.l - m.r) / (T - 1)))));
    cross.setAttribute("x1", x(t)); cross.setAttribute("x2", x(t)); cross.setAttribute("opacity", 0.5);
    const rows = names.slice().reverse().map((n) =>
      `<div class="r"><span><i style="background:${LAYER_COLORS[n]}"></i>${n}</span><span>${fmtM(cur.layers[n][t])}</span></div>`).join("");
    tip.innerHTML = `<b>${cur.summary.months[t]} · ${fmtM(totals[t])} subscribers</b>${rows}`;
    const br = box.getBoundingClientRect();
    placeTip(tip, box, e.clientX - br.left, e.clientY - br.top);
  });
  hit.addEventListener("mouseleave", () => { tip.style.display = "none"; cross.setAttribute("opacity", 0); });
  $("sub-legend").innerHTML = names.map((n) => `<span><i style="background:${LAYER_COLORS[n]}"></i>${n}</span>`).join("");
}

function walkChart(cur) {
  const box = $("walk-chart");
  box.querySelectorAll("svg").forEach((s) => s.remove());
  const d = cur.drivers, steps = d.walk_steps, yi = walkYear;
  const vals = steps.map((s) => d.walk[s][yi]);
  const yearLabel = "FY" + cur.summary.months[12 * yi].slice(0, 4);
  const lo = cur.checks.band[0] / cur.checks.cal_target, hi = cur.checks.band[1] / cur.checks.cal_target;
  const bars = [{ label: WALK_SHORT[steps[0]], from: 0, to: vals[0], total: true, name: steps[0] }];
  for (let i = 1; i < steps.length; i++) bars.push({ label: WALK_SHORT[steps[i]], from: vals[i - 1], to: vals[i], name: steps[i] });
  bars.push({ label: "Net", from: 0, to: vals[vals.length - 1], total: true, name: "Net revenue per paying subscriber" });
  const W = 720, H = 250, m = { l: 44, r: 112, t: 18, b: 26 };
  const [max, tick] = niceScale(Math.max(vals[0], hi) * 1.08);
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": `ARPU walk for ${yearLabel}` }, box);
  const y = (v) => m.t + (H - m.t - m.b) * (1 - v / max);
  gridlines(svg, y, max, tick, m.l, W - m.r, (v) => "$" + Math.round(v));
  const step = (W - m.l - m.r) / bars.length, bw = Math.min(52, step * 0.6);
  for (const [v, name] of [[lo, "$280M est."], [hi, "$450M est."]]) {
    el("line", { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), stroke: "var(--ink-2)", "stroke-width": 1, opacity: 0.7 }, svg);
    el("text", { x: W - m.r + 6, y: y(v) + 4, style: "fill: var(--ink-2)" }, svg).textContent = `$${v.toFixed(0)} · ${name}`;
  }
  const tip = tooltip(box);
  bars.forEach((b, i) => {
    const cx = m.l + step * (i + 0.5), top = Math.max(b.from, b.to), bot = Math.min(b.from, b.to);
    const h = Math.max(1.5, y(bot) - y(top));
    if (b.total) el("path", { d: roundTop(cx - bw / 2, y(top), bw, y(bot) - y(top), 4), fill: "var(--series-1)" }, svg);
    else el("rect", { x: cx - bw / 2, y: y(top), width: bw, height: h, rx: 3, fill: b.to < b.from ? "var(--ghost)" : "var(--c2025)" }, svg);
    if (i < bars.length - 1) {
      const nx = m.l + step * (i + 1.5) - bw / 2;
      el("line", { x1: cx + bw / 2, x2: nx, y1: y(b.to), y2: y(b.to), stroke: "var(--axis)", "stroke-width": 1 }, svg);
    }
    const delta = b.total ? `$${b.to.toFixed(2)}` : (b.to >= b.from ? "+" : "−") + "$" + Math.abs(b.to - b.from).toFixed(2);
    el("text", { x: cx, y: y(top) - 6, "text-anchor": "middle", style: "fill: var(--ink-2)" }, svg).textContent = delta;
    el("text", { x: cx, y: H - 8, "text-anchor": "middle" }, svg).textContent = b.label;
    const hit = el("rect", { x: cx - step / 2, y: m.t, width: step, height: H - m.t - m.b, fill: "transparent" }, svg);
    hit.addEventListener("mousemove", (e) => {
      const r = box.getBoundingClientRect();
      tip.innerHTML = `<b>${b.name}, ${yearLabel}</b><div class="r"><span>${b.total ? "Level" : "Change"}</span><span>${delta}</span></div>` +
        (b.total ? "" : `<div class="r"><span>After this step</span><span>$${b.to.toFixed(2)}</span></div>`);
      placeTip(tip, box, e.clientX - r.left, e.clientY - r.top);
    });
    hit.addEventListener("mouseleave", () => (tip.style.display = "none"));
  });
  const fees = Object.values(d.by_platform).reduce((a, v) => a + v.fees[yi], 0);
  const ios = d.by_platform.IOS.fees[yi];
  const counted = d.per_counted_sub[yi], paying = vals[vals.length - 1];
  $("walk-note").innerHTML = `App stores and card processors keep <b>${fmtUSD(fees)}</b> in ${yearLabel}, ${Math.round((100 * ios) / fees)}% of it Apple's. ` +
    (Math.abs(counted - paying) > 0.01 ? `Counting free-trial users as subscribers, net revenue per counted subscriber is <b>$${counted.toFixed(2)}</b>. ` : "") +
    `The model lands at $${paying.toFixed(0)}; reaching $${lo.toFixed(0)} needs a definition the drivers don't capture (see the reconciliation doc).`;
  $("walk-years").innerHTML = d.walk.FX.map((_, i) =>
    `<button type="button" role="tab" aria-selected="${i === yi}" data-i="${i}">FY${cur.summary.months[12 * i].slice(0, 4)}</button>`).join("");
  $("walk-years").querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
    walkYear = +b.dataset.i; walkChart(state.current); arpuTables(state.current);
  }));
}

function arpuTables(cur) {
  const d = cur.drivers, yi = walkYear, yl = "FY" + cur.summary.months[12 * yi].slice(0, 4);
  const rows = (labels, keys, vals) => keys.map((k, i) =>
    `<tr><td>${labels[k]}</td><td>$${vals[i][yi].toFixed(2)}</td><td>$${(vals[i][yi] / 12).toFixed(2)}</td></tr>`).join("");
  $("arpu-region").innerHTML = `<thead><tr><th>Region, ${yl}</th><th>$/sub/yr</th><th>$/mo</th></tr></thead><tbody>${rows(REGION_LABEL, d.regions, d.arpu_region)}</tbody>`;
  $("arpu-plan").innerHTML = `<thead><tr><th>Plan, ${yl}</th><th>$/sub/yr</th><th>$/mo</th></tr></thead><tbody>${rows(PLAN_LABEL, d.plans, d.arpu_plan)}</tbody>`;
}

// ---------- tiles, checks, table ----------
function tiles(cur, base, changed) {
  const yc = years(cur.summary), yb = years(base.summary);
  const last = yc.length - 1;
  const cagr = (ys) => Math.pow(ys[last].revenue / ys[0].revenue, 1 / last) - 1;
  const [lo, hi] = cur.checks.band;
  const inBand = yc[0].revenue >= lo && yc[0].revenue <= hi;
  const delta = (a, b, f) => (!changed ? "" : Math.abs(a - b) <= 1e-6 * Math.max(1, Math.abs(b)) ? "no change vs base"
    : signed(a - b, f) + " vs base");
  const items = [
    ["FY2025 net revenue", fmtUSD(yc[0].revenue), inBand ? "✓ inside public estimates" : "✕ outside $280–450M", inBand ? "good" : "bad"],
    [`FY${yc[last].year} net revenue`, fmtUSD(yc[last].revenue), delta(yc[last].revenue, yb[last].revenue, fmtUSD), ""],
    [`Subscribers, Dec ${yc[last].year}`, fmtM(yc[last].closing, 1), delta(yc[last].closing, yb[last].closing, (v) => fmtM(v, 2)), ""],
    [`Revenue CAGR ${yc[0].year}–${yc[last].year.slice(2)}`, (cagr(yc) * 100).toFixed(1) + "%",
      delta(cagr(yc) * 100, cagr(yb) * 100, (v) => v.toFixed(1) + " pts"), ""],
  ];
  $("tiles").innerHTML = items.map(([l, v, n, c]) =>
    `<div class="card tile"><div class="label">${l}</div><div class="value">${v}</div><div class="note ${c}">${n}</div></div>`).join("");
}

function checks(cur) {
  const c = cur.checks;
  const rows = [
    ["Subscribers roll forward every month", c.rollforward_gap < 1, `max gap ${c.rollforward_gap.toExponential(1)}`],
    ["Cohorts tie to the subscriber total", c.cohort_tie_gap < 1 && c.layers_tie_gap < 1, `max gap ${Math.max(c.cohort_tie_gap, c.layers_tie_gap).toExponential(1)}`],
    ["Subscribers within the 7.3M anchor band (Jun 2025)", c.cal_subs >= c.cal_band[0] && c.cal_subs <= c.cal_band[1],
      `${fmtM(c.cal_subs, 3)} vs ${fmtM(c.cal_band[0])}–${fmtM(c.cal_band[1])}`],
    ["FY2025 revenue inside public estimates", c.fy1_revenue >= c.band[0] && c.fy1_revenue <= c.band[1], `${fmtUSD(c.fy1_revenue)} vs $280–450M`],
  ];
  $("checks").innerHTML = rows.map(([l, ok, d]) =>
    `<li class="${ok ? "ok" : "no"}"><span class="ic" aria-hidden="true">${ok ? "✓" : "✕"}</span><span>${l} <span class="sr">${ok ? "(pass)" : "(fail)"}</span></span><span class="detail">${d}</span></li>`).join("");
}

function table(cur) {
  const ys = years(cur.summary);
  const head = ["", ...ys.map((d) => d.year)];
  const rows = [
    ["Opening", (d) => fmtM(d.opening)], ["+ New", (d) => fmtM(d.new)], ["+ Reactivated", (d) => fmtM(d.reactivated)],
    ["− Churned", (d) => fmtM(d.churned)], ["= Closing", (d) => fmtM(d.closing)],
    ["Net revenue", (d) => fmtUSD(d.revenue)], ["Net $/paying sub/yr", (d) => "$" + d.arpu.toFixed(2)],
  ];
  $("table").innerHTML = `<thead><tr>${head.map((h) => `<th>${h}</th>`).join("")}</tr></thead><tbody>` +
    rows.map(([l, f]) => `<tr><td>${l}</td>${ys.map((d) => `<td>${f(d)}</td>`).join("")}</tr>`).join("") + "</tbody>";
}

function render() {
  const changed = isChanged();
  revenueChart(state.current, state.base, changed);
  walkChart(state.current);
  arpuTables(state.current);
  subscriberChart(state.current);
  tiles(state.current, state.base, changed);
  checks(state.current);
  table(state.current);
}

// ---------- controls ----------
function setFx(v) {
  state.params.fx_shock_dir = v;
  $("fx").querySelectorAll("button").forEach((b) => b.setAttribute("aria-checked", String(+b.dataset.v === v)));
}

function isChanged() {
  return state.sliders.some((s) => state.params[s.key] !== state.params0[s.key]) ||
    state.params.count_trials_as_subs !== state.params0.count_trials_as_subs || !$("recal").checked ||
    state.params.fx_shock_dir !== state.params0.fx_shock_dir;
}

function buildSliders() {
  $("sliders").innerHTML = state.sliders.map((s, i) => {
    const step = (s.high - s.low) / 100;
    return `<div class="slider">
      <div class="row"><label for="s${i}">${s.label}</label><span class="val" id="v${i}">${fmtVal(s.key, s.value)}</span></div>
      <input type="range" id="s${i}" min="${s.low}" max="${s.high}" step="${step}" value="${s.value}"
        title="Sources: ${s.sources} · as of ${s.as_of}">
      <div class="src"><span>${fmtVal(s.key, s.low)} – ${fmtVal(s.key, s.high)}</span><span class="chip">${s.status}</span></div>
    </div>`;
  }).join("");
  state.sliders.forEach((s, i) => {
    $(`s${i}`).addEventListener("input", (e) => {
      const v = parseFloat(e.target.value);
      state.params[s.key] = Math.abs(v - s.value) < 1e-9 ? s.value : v;
      $(`v${i}`).textContent = fmtVal(s.key, v);
      $(`v${i}`).classList.toggle("changed", state.params[s.key] !== s.value);
      schedule();
    });
  });
}

let timer = null;
function schedule() { clearTimeout(timer); timer = setTimeout(recompute, 60); }

async function recompute() {
  if (!state.py) return;
  if (state.busy) { state.queued = true; return; }
  state.busy = true;
  try {
    const k = $("recal").checked ? "None" : String(state.base.summary.k_cal);
    state.py.globals.set("p_json", JSON.stringify(state.params));
    state.current = JSON.parse(state.py.runPython(`json.dumps(cohorts.payload(json.loads(p_json), ${k}))`));
    render();
  } catch (err) {
    console.error(err);
    $("engine-text").textContent = "Engine error: " + String(err.message || err).split("\n").slice(-2).join(" ");
  } finally {
    state.busy = false;
    if (state.queued) { state.queued = false; recompute(); }
  }
}

async function startEngine() {
  try {
    await new Promise((res, rej) => {
      const s = document.createElement("script");
      s.src = PYODIDE + "pyodide.js"; s.onload = res; s.onerror = () => rej(new Error("could not load Pyodide"));
      document.head.appendChild(s);
    });
    const py = await loadPyodide({ indexURL: PYODIDE });
    await py.loadPackage("numpy");
    const src = await (await fetch("engine/cohorts.py")).text();
    py.FS.writeFile("cohorts.py", src);
    py.runPython("import sys, json; sys.path.insert(0, '.'); import cohorts");
    state.py = py;
    $("engine").classList.add("live");
    $("engine-text").textContent = "Live: the Python engine is running in your browser";
    $("controls").disabled = false;
    if (isChanged()) recompute();
  } catch (err) {
    $("engine-text").textContent = "Couldn't load the in-browser engine; showing the precomputed base case.";
    console.error(err);
  }
}

async function main() {
  const data = await (await fetch("data/base.json")).json();
  state.base = data.base;
  state.current = data.base;
  state.params0 = data.params;
  state.params = structuredClone(data.params);
  state.sliders = data.sliders;
  buildSliders();
  $("trials").checked = !!state.params0.count_trials_as_subs;
  $("trials").addEventListener("change", (e) => { state.params.count_trials_as_subs = e.target.checked ? 1 : 0; schedule(); });
  $("recal").addEventListener("change", schedule);
  $("fx").querySelectorAll("button").forEach((b) => b.addEventListener("click", () => { setFx(+b.dataset.v); schedule(); }));
  $("reset").addEventListener("click", () => {
    state.params = structuredClone(state.params0);
    setFx(state.params0.fx_shock_dir);
    $("recal").checked = true;
    $("trials").checked = !!state.params0.count_trials_as_subs;
    buildSliders();
    state.current = state.base;
    render();
  });
  render();
  let resizeTimer;
  window.addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(render, 150); });
  startEngine();
}
main();
