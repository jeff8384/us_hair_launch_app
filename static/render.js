import { AXES, COLOR, RETAILER, snippet } from "./metrics.js";

export const $ = (id) => document.getElementById(id);

export function renderRadar(series) {
  $("radar").replaceChildren(radarSvg(series));
  $("legend").replaceChildren(...series.map((item) => {
    const label = el("span", "");
    const mark = el("i", "");
    mark.style.background = item.color;
    label.append(mark, document.createTextNode(item.label));
    return label;
  }));
}

export function renderList(id, items) {
  $(id).replaceChildren(...(items?.length ? items : ["해당 항목 없음"]).map((item) => textEl("li", "", item)));
}

export function renderFlags(flags) {
  $("flagPanel").hidden = flags.length === 0;
  $("flags").replaceChildren(...flags.map((flag) => {
    const row = el("div", "flag");
    row.append(textEl("code", "", flag.term), textEl("span", "", `→ ${flag.fix}`));
    return row;
  }));
}

export function renderRewrites(rewrites) {
  $("rewrites").replaceChildren(...rewrites.map((rewrite) => {
    const card = el("article", `rw ${rewrite.label === "compliance_safe" ? "safe" : ""}`);
    card.append(textEl("div", "rw-lb", rewrite.label), textEl("div", "rw-tx", rewrite.text));
    return card;
  }));
}

export function rivalCard(item, axis, mine) {
  const claim = item.claim;
  const delta = axis ? item.scores[axis] - (mine?.[axis] || 0) : null;
  const card = el("article", "rv");
  const head = el("div", "rv-hd");
  const dot = el("i", "rv-dot");
  dot.style.background = COLOR[claim.retailer] || "#8c8194";
  head.append(dot, textEl("span", "rv-brand", claim.brand || RETAILER[claim.retailer] || claim.retailer));
  if (item.similarity != null) head.append(textEl("span", "rv-sim", `유사도 ${Math.round(item.similarity * 100)}%`));
  if (delta != null) head.append(textEl("span", `rv-delta ${delta > 0 ? "up" : delta < 0 ? "dn" : ""}`, `${delta > 0 ? "+" : ""}${delta} vs 내 문안`));
  card.append(head, textEl("div", "rv-p", claim.product_name || "(unnamed product)"));
  card.append(textEl("div", "rv-q", `“${snippet(claim).slice(0, 190)}${snippet(claim).length > 190 ? "..." : ""}”`));
  return card;
}

function radarSvg(series) {
  const svg = svgEl("svg", { viewBox: "0 0 340 340", role: "img", "aria-label": "포지셔닝 레이더" });
  const center = 170;
  const radius = 112;
  for (const step of [25, 50, 75, 100]) {
    svg.append(svgEl("polygon", { points: polygonPoints(scaleScores(step), center, radius), fill: "none", stroke: "#e3dbe4" }));
  }
  AXES.forEach((axis, index) => {
    const end = point(index, 100, center, radius);
    const label = point(index, 133, center, radius);
    svg.append(svgEl("line", { x1: center, y1: center, x2: end.x, y2: end.y, stroke: "#e3dbe4" }));
    const text = svgEl("text", { x: label.x, y: label.y, "text-anchor": "middle", "dominant-baseline": "middle" });
    text.textContent = axis[1];
    svg.append(text);
  });
  for (const item of series) {
    svg.append(svgEl("polygon", {
      points: polygonPoints(item.scores, center, radius),
      fill: item.color,
      "fill-opacity": item.key === "draft" ? "0.20" : "0.07",
      stroke: item.color,
      "stroke-width": item.key === "draft" ? "2.4" : "1.4",
      "stroke-dasharray": item.key === "draft" ? "none" : "3 3",
    }));
  }
  return svg;
}

function scaleScores(value) {
  return Object.fromEntries(AXES.map(([axis]) => [axis, value]));
}

function polygonPoints(scores, center, radius) {
  return AXES.map(([axis], index) => {
    const p = point(index, scores[axis] || 0, center, radius);
    return `${p.x},${p.y}`;
  }).join(" ");
}

function point(index, value, center, radius) {
  const angle = -Math.PI / 2 + (index * 2 * Math.PI) / AXES.length;
  const scaled = (value / 100) * radius;
  return { x: center + scaled * Math.cos(angle), y: center + scaled * Math.sin(angle) };
}

export function el(tag, className) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  return node;
}

export function textEl(tag, className, text) {
  const node = el(tag, className);
  node.textContent = text;
  return node;
}

function svgEl(tag, attrs) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  return node;
}
