export const AXES = [
  ["science", "과학·기술"],
  ["clinical", "임상 검증·CRO"],
  ["ingredient", "성분 히어로"],
  ["sensorial", "감각·프리미엄"],
  ["clean", "클린·안전"],
  ["authority", "전문가·살롱"],
  ["social", "사회적 증거"],
  ["problem", "문제·해결"],
];

export const RETAILER = { sephora: "Sephora", ulta: "Ulta", other: "기타", unknown: "미상" };
export const COLOR = { sephora: "#17161a", ulta: "#da6a2c", draft: "#a62e5c" };

export function scopedClaims(claims, topN, disabledSources) {
  const counts = {};
  return claims.filter((claim) => {
    const source = sourceName(claim);
    counts[claim.retailer] = (counts[claim.retailer] || 0) + 1;
    return counts[claim.retailer] <= topN && !disabledSources.has(source);
  });
}

export function sourceName(claim) {
  const note = (claim.evidence_notes || []).find((item) => item.startsWith("Raw provenance "));
  if (!note) return "unknown";
  const path = note.replace("Raw provenance ", "");
  return path.split("/")[0] || "unknown";
}

export function buildSources(preview, claims) {
  const byFile = new Map((preview?.files || []).map((file) => [
    file.filename,
    { name: file.filename, n: 0, sheets: file.sheets, retailers: new Set([file.retailer_hint]) },
  ]));
  for (const claim of claims || []) {
    const name = sourceName(claim);
    const entry = byFile.get(name) || { name, n: 0, sheets: [], retailers: new Set() };
    entry.n += 1;
    entry.retailers.add(claim.retailer);
    byFile.set(name, entry);
  }
  return [...byFile.values()];
}

export function groupByRetailer(claims) {
  return claims.reduce((groups, claim) => {
    groups[claim.retailer] ||= [];
    groups[claim.retailer].push(claim);
    return groups;
  }, {});
}

export function averageScores(claims) {
  const totals = Object.fromEntries(AXES.map(([axis]) => [axis, 0]));
  for (const claim of claims) {
    const scores = scoreClaim(claim);
    for (const [axis] of AXES) totals[axis] += scores[axis];
  }
  for (const [axis] of AXES) totals[axis] = Math.round(totals[axis] / Math.max(1, claims.length));
  return totals;
}

export function averageCoverage(claims) {
  const totals = Object.fromEntries(AXES.map(([axis]) => [axis, 0]));
  for (const claim of claims) {
    const scores = scoreClaim(claim);
    for (const [axis] of AXES) if (scores[axis] >= 30) totals[axis] += 1;
  }
  for (const [axis] of AXES) {
    totals[axis] = Math.round((totals[axis] / Math.max(1, claims.length)) * 100);
  }
  return totals;
}

export function scoreClaim(claim) {
  const proof = new Set(claim.proof_type || []);
  const benefits = new Set(claim.benefit_keywords || []);
  const sensory = new Set(claim.sensory_keywords || []);
  const concerns = new Set(claim.target_concerns || []);
  return {
    science: clamp(intersection(proof, ["formulation", "ingredient"]) * 34),
    clinical: clamp(intersection(proof, ["clinical", "consumer_test", "before_after"]) * 34),
    ingredient: clamp((claim.ingredients_called_out || []).length * 18),
    sensorial: clamp((sensory.size * 22) + (benefits.has("shine") ? 25 : 0)),
    clean: clamp(claim.visual_style === "clean-minimal" ? 65 : 0),
    authority: clamp(intersection(proof, ["award_press", "expert"]) ? 65 : 0),
    social: clamp(intersection(proof, ["review_social_proof", "award_press"]) ? 70 : 0),
    problem: clamp(new Set([...benefits, ...concerns]).size * 12),
  };
}

export function axisLeaders(claims, axis, limit = 4) {
  return claims
    .map((claim) => ({ claim, scores: scoreClaim(claim) }))
    .filter((item) => item.scores[axis] > 0 && snippet(item.claim))
    .sort((a, b) => b.scores[axis] - a.scores[axis])
    .slice(0, limit);
}

export function nearestRivals(claims, mine, limit = 3) {
  return claims
    .map((claim) => ({ claim, scores: scoreClaim(claim) }))
    .filter((item) => snippet(item.claim))
    .map((item) => ({ ...item, similarity: cosine(mine, item.scores) }))
    .sort((a, b) => b.similarity - a.similarity)
    .slice(0, limit);
}

export function snippet(claim) {
  return [claim.hero_claim, ...(claim.supporting_claims || [])].filter(Boolean).join(" / ");
}

function cosine(a, b) {
  let dot = 0;
  let na = 0;
  let nb = 0;
  for (const [axis] of AXES) {
    dot += (a[axis] || 0) * (b[axis] || 0);
    na += (a[axis] || 0) ** 2;
    nb += (b[axis] || 0) ** 2;
  }
  return na && nb ? dot / Math.sqrt(na * nb) : 0;
}

function intersection(set, values) {
  return values.filter((value) => set.has(value)).length;
}

function clamp(value) {
  return Math.max(0, Math.min(100, Math.round(value)));
}
