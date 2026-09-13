const awardId = "CYA-2026-017";
const $ = (selector) => document.querySelector(selector);

const els = {
  run: $("#runButton"), reset: $("#resetButton"), empty: $("#emptyState"), review: $("#reviewLayout"),
  findings: $("#findingsList"), findingCount: $("#findingCount"), decision: $("#decisionCard"),
  findingsLabel: $("#findingsLabel"),
  verified: $("#verifiedCard"), approve: $("#approveButton"), keepBlocked: $("#keepBlockedButton"),
  trail: $("#eventTrail"), trailEmpty: $("#trailEmpty"), evidenceTable: $("#evidenceTable"),
  proofStatus: $("#proofStatus"), statusTitle: $("#statusTitle"), blockerMetric: $("#blockerMetric"),
  evidenceMetric: $("#evidenceMetric"), coverageMetric: $("#coverageMetric"), agentMode: $("#agentMode"),
  manifestCount: $("#manifestCount"), toast: $("#toast")
};

function money(value) { return value == null ? "—" : `$${Number(value).toLocaleString("en-US", {minimumFractionDigits: 2})}`; }
function humanKind(value) { return value.replaceAll("_", " ").replace(/\b\w/g, c => c.toUpperCase()); }
function showToast(message) {
  els.toast.textContent = message; els.toast.classList.add("show");
  window.clearTimeout(showToast.timer); showToast.timer = window.setTimeout(() => els.toast.classList.remove("show"), 3200);
}

async function api(path, options = {}) {
  const response = await fetch(path, {headers: {"Content-Type": "application/json"}, ...options});
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return response.json();
}

function renderEvidence(state) {
  els.manifestCount.textContent = `${state.evidence.length} artifacts`;
  els.evidenceTable.innerHTML = state.evidence.map(item => {
    let value = "—";
    if (item.amount != null) value = money(item.amount);
    if (item.participant_ids?.length) value = `${item.participant_ids.length} youth`;
    const verified = state.status === "verified" && item.status === "included" ? " verified" : "";
    return `<tr>
      <td>${item.filename}<span class="file-sub">${item.id} · ${item.sha256.slice(0, 10)}…</span></td>
      <td>${humanKind(item.kind)}</td><td>${value}</td><td>${item.captured_on}</td>
      <td><span class="status-chip ${item.status}${verified}">${state.status === "verified" && item.status === "included" ? "Verified" : humanKind(item.status)}</span></td>
    </tr>`;
  }).join("");
}

function renderFindings(state) {
  els.findingsLabel.textContent = state.status === "verified" ? "Resolved findings" : "Blocking findings";
  els.findingCount.textContent = state.findings.length;
  els.findings.innerHTML = state.findings.map((finding, index) => `<article class="finding ${state.status === "verified" ? "resolved" : ""}" style="animation-delay:${index * 70}ms">
    <div class="finding-index">${state.status === "verified" ? "✓" : String(index + 1).padStart(2, "0")}</div>
    <div><h4>${finding.title}</h4><p>${finding.detail}</p>
      <div class="finding-evidence">${finding.evidence_ids.map(id => `<span>${id}</span>`).join("")}</div></div>
    <div class="finding-values">${finding.observed ? `<div><small>Observed</small><strong class="bad">${finding.observed}</strong></div>` : ""}${finding.expected ? `<div><small>Expected</small><strong>${finding.expected}</strong></div>` : ""}</div>
  </article>`).join("");
}

function renderDecision(state) {
  els.decision.classList.toggle("hidden", !state.decision || state.status === "verified");
  els.verified.classList.toggle("hidden", state.status !== "verified");
  if (!state.decision || state.status === "verified") return;
  $("#decisionTitle").textContent = state.decision.title;
  $("#decisionSummary").textContent = state.decision.summary;
  $("#decisionRecommendation").textContent = state.decision.recommendation;
  $("#decisionConsequences").innerHTML = state.decision.consequences.map(item => `<li>${item}</li>`).join("");
  $("#approveLabel").textContent = state.decision.action_label;
}

function renderTrail(state) {
  els.trailEmpty.classList.toggle("hidden", state.events.length > 0);
  els.trail.innerHTML = state.events.map(event => `<li class="${event.kind}"><strong>${event.title}</strong><p>${event.detail}</p><code>${event.tool}</code></li>`).join("");
}

function render(state) {
  const started = state.status !== "ready";
  els.empty.classList.toggle("hidden", started);
  els.review.classList.toggle("hidden", !started);
  els.proofStatus.dataset.status = state.status;
  els.statusTitle.textContent = state.status === "ready" ? "Ready to audit" : state.status === "blocked" ? "Blocked — review needed" : state.status === "verified" ? "Verified with evidence" : "Audit in progress";
  els.blockerMetric.textContent = state.status === "ready" ? "—" : state.metrics.unsupported_material_claims;
  els.evidenceMetric.textContent = state.metrics.evidence_files;
  els.coverageMetric.textContent = `${state.metrics.requirements_covered} / ${state.metrics.total_requirements}`;
  els.agentMode.textContent = state.agent_mode === "agentcore" ? "LIVE AGENTCORE LOOP" : state.agent_mode === "strands" ? "LIVE BEDROCK LOOP" : "DETERMINISTIC TWIN";
  els.run.disabled = started;
  els.run.querySelector("span").textContent = state.status === "ready" ? "Run evidence audit" : state.status === "verified" ? "Audit complete" : "Audit paused for review";
  renderEvidence(state); renderFindings(state); renderDecision(state); renderTrail(state);
}

async function load() { render(await api("/api/state")); }

els.run.addEventListener("click", async () => {
  els.run.disabled = true; els.run.querySelector("span").textContent = "Inspecting evidence…";
  try {
    await api(`/api/audits/${awardId}/run`, {method: "POST"}); await load();
    $("#reviewLayout").scrollIntoView({behavior: "smooth", block: "start"});
    showToast("Audit paused safely: one human decision is ready.");
  } catch (error) { showToast(error.message); els.run.disabled = false; }
});

els.approve.addEventListener("click", async () => {
  els.approve.disabled = true; $("#approveLabel").textContent = "Applying bounded correction…";
  try {
    const state = await api("/api/state");
    await api(`/api/audits/${awardId}/resolve`, {method: "POST", body: JSON.stringify({decision_id: state.decision.id, approve: true})});
    await load(); showToast("Fresh verification passed. Evidence packet is ready.");
  } catch (error) { showToast(error.message); els.approve.disabled = false; }
});

els.keepBlocked.addEventListener("click", async () => {
  try {
    const state = await api("/api/state");
    await api(`/api/audits/${awardId}/resolve`, {method: "POST", body: JSON.stringify({decision_id: state.decision.id, approve: false})});
    await load(); showToast("Report remains blocked. No records were changed.");
  } catch (error) { showToast(error.message); }
});

els.reset.addEventListener("click", async () => {
  await api("/api/reset", {method: "POST"}); await load(); showToast("Demo restored to the original evidence inbox."); window.scrollTo({top: 0, behavior: "smooth"});
});

load().catch(error => showToast(error.message));
