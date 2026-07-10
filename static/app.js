import {
  AXES,
  COLOR,
  RETAILER,
  averageCoverage,
  averageScores,
  axisLeaders,
  buildSources,
  groupByRetailer,
  nearestRivals,
  scopedClaims,
} from "./metrics.js";
import { $, el, renderFlags, renderList, renderRadar, renderRewrites, rivalCard, textEl } from "./render.js";

const state = {
  preview: null,
  artifacts: null,
  disabledSources: new Set(),
  topN: 30,
  selectedAxis: null,
  lastReview: null,
};

async function init() {
  bindEvents();
  await refreshData(false);
}

function bindEvents() {
  $("runButton").addEventListener("click", () => refreshData(true));
  $("reviewButton").addEventListener("click", reviewDraft);
  $("axisClose").addEventListener("click", () => selectAxis(null));
  $("topN").addEventListener("input", () => {
    state.topN = Number($("topN").value);
    $("topNValue").textContent = `${state.topN}위`;
    state.lastReview = null;
    $("resultSection").hidden = true;
    renderProfiles();
  });
}

async function refreshData(runPipeline) {
  setError("");
  setBusy($("runButton"), true, "Refreshing");
  try {
    if (runPipeline) {
      const params = new URLSearchParams({ ai_backend: $("backendSelect").value });
      await fetchJson(`/api/run?${params}`, { method: "POST" });
    }
    const [preview, artifacts] = await Promise.all([fetchJson("/api/preview"), fetchJson("/api/artifacts")]);
    state.preview = preview;
    state.artifacts = artifacts;
    state.disabledSources.clear();
    renderSources();
    renderProfiles();
    providerNote("Ready", artifacts?.pdp_blocks?.ai_assist?.backend || "local-first");
  } catch (error) {
    setError(error.message);
  } finally {
    setBusy($("runButton"), false, "Refresh data");
  }
}

async function reviewDraft() {
  const copy = $("draftCopy").value.trim();
  if (!copy) {
    setError("검토할 문안을 입력해 주세요.");
    return;
  }
  setError("");
  setBusy($("reviewButton"), true, "검토 중...");
  try {
    const review = await fetchJson("/api/review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        product_name: $("productName").value.trim(),
        category: $("category").value,
        copy,
        ai_backend: $("backendSelect").value,
        top_n: state.topN,
      }),
    });
    state.lastReview = review;
    renderReview(review);
    providerNote(review.backend, review.diagnostics?.[0] || "Local AI preferred; deterministic fallback remains available.");
  } catch (error) {
    setError(error.message);
  } finally {
    setBusy($("reviewButton"), false, "문안 검토 요청");
  }
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

function renderSources() {
  const sources = buildSources(state.preview, state.artifacts?.claims || []);
  $("sourceList").replaceChildren(...sources.map((source) => {
    const row = el("article", `src ${state.disabledSources.has(source.name) ? "off" : ""}`);
    const dots = el("div", "src-dots");
    for (const retailer of source.retailers) {
      const dot = el("i", "");
      dot.style.background = COLOR[retailer] || "#8c8194";
      dots.append(dot);
    }
    const body = el("div", "src-body");
    body.append(textEl("div", "src-n", source.name));
    body.append(textEl("div", "src-m", `${source.n || 0}행 · ${[...source.retailers].map((r) => RETAILER[r] || r).join(", ")}`));
    const toggle = textEl("button", "src-tog", state.disabledSources.has(source.name) ? "사용" : "제외");
    toggle.type = "button";
    toggle.addEventListener("click", () => toggleSource(source.name));
    row.append(dots, body, toggle);
    return row;
  }));
}

function toggleSource(source) {
  if (state.disabledSources.has(source)) state.disabledSources.delete(source);
  else state.disabledSources.add(source);
  state.lastReview = null;
  $("resultSection").hidden = true;
  renderSources();
  renderProfiles();
}

function renderProfiles() {
  const claims = scopedClaims(state.artifacts?.claims || [], state.topN, state.disabledSources);
  const groups = groupByRetailer(claims);
  const retailers = Object.keys(groups);
  $("scopeCount").textContent = `${claims.length}개 제품 · 상위 ${state.topN}위`;
  $("profileCards").replaceChildren(...retailers.map((retailer) => {
    const scores = averageScores(groups[retailer]);
    const leaders = AXES.slice().sort((a, b) => scores[b[0]] - scores[a[0]]).slice(0, 2);
    const card = el("article", "prof-card");
    const dot = el("i", "dot");
    dot.style.background = COLOR[retailer] || "#8c8194";
    card.append(dot, textEl("div", "prof-name", RETAILER[retailer] || retailer));
    card.append(textEl("div", "prof-n", `${groups[retailer].length}개 제품`));
    card.append(textEl("div", "prof-lead", `강조 축 · ${leaders.map((item) => item[1]).join(" · ")}`));
    return card;
  }));
}

function renderReview(review) {
  $("resultSection").hidden = false;
  $("summary").textContent = review.summary;
  $("riskValue").textContent = String(review.compliance?.risk || "-").toUpperCase();
  $("riskBox").style.setProperty("--risk", riskColor(review.compliance?.risk));
  renderPositioning(review);
  renderCoverage(review.scores);
  renderNearest(review.scores);
  renderList("diffList", review.differentiation);
  renderList("crowdedList", review.crowded);
  renderList("gapList", review.gaps);
  renderFlags(review.compliance?.flags || []);
  renderRewrites(review.rewrites || []);
  selectAxis(null);
}

function renderPositioning(review) {
  const groups = groupByRetailer(currentClaims());
  const series = Object.entries(groups).map(([retailer, claims]) => ({
    key: retailer,
    label: `${RETAILER[retailer] || retailer} 평균`,
    color: COLOR[retailer] || "#8c8194",
    scores: averageScores(claims),
  }));
  series.push({ key: "draft", label: "내 문안", color: COLOR.draft, scores: review.scores });
  renderRadar(series);
}

function renderCoverage(draftScores) {
  const coverage = averageCoverage(currentClaims());
  $("coverageBars").replaceChildren(...AXES.map(([axis, label]) => {
    const competitor = coverage[axis] || 0;
    const mine = draftScores[axis] || 0;
    const row = textEl("button", `bar-row ${state.selectedAxis === axis ? "sel" : ""}`, "");
    row.type = "button";
    row.setAttribute("aria-pressed", String(state.selectedAxis === axis));
    row.addEventListener("click", () => selectAxis(state.selectedAxis === axis ? null : axis));
    const track = el("span", "bar-track");
    const fill = el("span", "bar-fill");
    const marker = el("span", "bar-mine");
    fill.style.width = `${competitor}%`;
    marker.style.left = `${mine}%`;
    track.append(fill, marker);
    row.append(textEl("span", "bar-label", label), track, textEl("span", `bar-tag ${tagClass(competitor, mine)}`, tagText(competitor, mine)));
    return row;
  }), textEl("div", "bars-hint", "축을 누르면 그 축을 강하게 쓰는 실제 경쟁 문안이 아래에 표시됩니다."));
}

function selectAxis(axis) {
  state.selectedAxis = axis;
  if (!state.lastReview) return;
  renderCoverage(state.lastReview.scores);
  $("axisPanel").hidden = !axis;
  if (!axis) return;
  const label = AXES.find(([key]) => key === axis)?.[1] || axis;
  const leaders = axisLeaders(currentClaims(), axis);
  $("axisTitle").textContent = `“${label}” 축을 가장 강하게 쓰는 경쟁 제품`;
  $("axisNote").textContent = `내 문안 ${state.lastReview.scores[axis] || 0}점 · 상위 ${state.topN}위 안의 실제 문안입니다.`;
  $("axisRivals").replaceChildren(...(leaders.length ? leaders.map((item) => rivalCard(item, axis, state.lastReview.scores)) : [textEl("div", "fc-empty", "이 축을 쓰는 경쟁 제품이 없습니다.")]));
}

function renderNearest(scores) {
  $("nearestRivals").replaceChildren(...nearestRivals(currentClaims(), scores).map((item) => rivalCard(item)));
}

function currentClaims() {
  return scopedClaims(state.artifacts?.claims || [], state.topN, state.disabledSources);
}

function providerNote(backend, detail) {
  $("providerNote").replaceChildren(textEl("span", "prov-lb", "AI backend"), textEl("span", "prov-pill on", backend), textEl("span", "prov-pill", detail));
}

function tagClass(comp, mine) {
  if (mine >= 30 && comp < 40) return "ws";
  if (mine >= 30 && comp >= 60) return "cr";
  return "";
}

function tagText(comp, mine) {
  if (mine >= 30 && comp < 40) return "여백 선점";
  if (mine >= 30 && comp >= 60) return "혼잡";
  return mine >= 30 ? "사용" : "미사용";
}

function riskColor(risk) {
  return { low: "#2e7d5b", medium: "#c58a22", high: "#b23a44" }[risk] || "#8c8194";
}

function setBusy(button, busy, text) {
  button.disabled = busy;
  button.textContent = text;
}

function setError(message) {
  $("errorBox").hidden = !message;
  $("errorBox").textContent = message;
}

init().catch((error) => setError(error.message));
