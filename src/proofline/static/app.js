const awardId = "CYA-2026-017";
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const sessionKey = "proofline-workspace-session";
let sessionId = sessionStorage.getItem(sessionKey);
if (!sessionId) {
  sessionId = globalThis.crypto?.randomUUID?.() || `proofline-${Date.now()}`;
  sessionStorage.setItem(sessionKey, sessionId);
}

let state = null;
let currentFilter = "all";
let intakeStep = 1;
let currentReportId = awardId;
const customReportsKey = "proofline-custom-reports";
const customReports = JSON.parse(localStorage.getItem(customReportsKey) || "[]");

const baseReports = [
  {id: awardId, title: "Community Youth Access Grant", funder: "City Office of Youth Programs", period: "Jul 1–Sep 30, 2026", shortPeriod: "Q3 2026", due: "Oct 15", dueMeta: "31 days", coverage: 0, status: "preparing", evidence: 5},
  {id: "DSA-2026-044", title: "Digital Skills Access Fund", funder: "Northbridge Foundation", period: "Jul 1–Sep 30, 2026", shortPeriod: "Q3 2026", due: "Oct 5", dueMeta: "21 days", coverage: 78, status: "preparing", evidence: 12},
  {id: "CFS-2026-008", title: "Community Food Security Initiative", funder: "State Department of Health", period: "Jul 1–Sep 30, 2026", shortPeriod: "Q3 2026", due: "Oct 31", dueMeta: "47 days", coverage: 65, status: "preparing", evidence: 18},
  {id: "SRT-2026-012", title: "Safe Routes Partnership", funder: "County Transportation Authority", period: "Apr 1–Jun 30, 2026", shortPeriod: "Q2 2026", due: "Sep 30", dueMeta: "Complete", coverage: 100, status: "verified", evidence: 9},
];

const routeLabels = {
  dashboard: ["Workspace", "Dashboard"], reports: ["Workspace", "Reports"], report: ["Reports", "Report workspace"],
  evidence: ["Workspace", "Evidence library"], decisions: ["Workspace", "Decisions"], analytics: ["Workspace", "Analytics"],
  integrations: ["Admin", "Integrations"], settings: ["Admin", "Policies & settings"],
};

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));
}
function money(value) { return value == null ? "—" : `$${Number(value).toLocaleString("en-US", {minimumFractionDigits: 2, maximumFractionDigits: 2})}`; }
function humanKind(value) { return String(value).replaceAll("_", " ").replace(/\b\w/g, char => char.toUpperCase()); }
function formatDate(value) { return new Date(`${value}T00:00:00`).toLocaleDateString("en-US", {month:"short", day:"numeric", year:"numeric"}); }
function statusLabel(status) { return ({attention:"Needs attention", preparing:"Preparing", verified:"Verified", draft:"Draft"})[status] || humanKind(status); }
function showToast(message) {
  const toast = $("#toast"); toast.textContent = message; toast.classList.add("show");
  clearTimeout(showToast.timer); showToast.timer = setTimeout(() => toast.classList.remove("show"), 3300);
}

async function api(path, options = {}) {
  const response = await fetch(path, {...options, headers:{"Content-Type":"application/json", "X-Proofline-Session":sessionId, ...(options.headers || {})}});
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return response.json();
}

function portfolioReports() {
  const cya = baseReports[0];
  if (state) {
    cya.coverage = Math.round((Number(state.metrics.requirements_covered) / Number(state.metrics.total_requirements || 1)) * 100);
    cya.status = state.status === "blocked" ? "attention" : state.status === "verified" ? "verified" : "preparing";
    cya.evidence = state.evidence.length;
  }
  return [...customReports, ...baseReports];
}

function route(name, updateHash = true) {
  if (!routeLabels[name]) name = "dashboard";
  $$(".page").forEach(page => page.classList.toggle("active", page.dataset.page === name));
  $$(".primary-nav a").forEach(link => link.classList.toggle("active", link.dataset.route === name || (name === "report" && link.dataset.route === "reports")));
  const [group, label] = routeLabels[name];
  $("#breadcrumbs").innerHTML = `<span>${group}</span><i>/</i><strong>${label}</strong>`;
  $("#sidebar").classList.remove("open");
  if (updateHash) history.replaceState(null, "", `#${name}`);
  window.scrollTo({top:0, behavior:"smooth"});
}

function renderPortfolio() {
  const reports = portfolioReports();
  $("#reportNavCount").textContent = reports.length;
  $("#reportsDueMetric").textContent = reports.filter(report => report.status !== "verified").length;
  $("#reportsDueMetric").nextElementSibling.textContent = "Next 60 days";
  const dashboard = reports.slice(0, 4);
  $("#dashboardReports").innerHTML = dashboard.map(report => `<div class="report-row" data-report-id="${escapeHtml(report.id)}">
    <div><strong>${escapeHtml(report.title)}</strong><small>${escapeHtml(report.funder)}</small></div>
    <div class="coverage-mini"><i><span style="width:${report.coverage}%"></span></i><b>${report.coverage}%</b></div>
    <div class="due-cell"><strong class="${report.status === "attention" ? "urgent" : ""}">${escapeHtml(report.due)}</strong><small>${escapeHtml(report.dueMeta)}</small></div>
    <span class="status-pill ${report.status}">${statusLabel(report.status)}</span><span class="row-arrow"><svg viewBox="0 0 24 24"><path d="m9 18 6-6-6-6"/></svg></span>
  </div>`).join("");
  renderReportTable();
}

function renderReportTable() {
  const query = ($("#reportSearch")?.value || "").trim().toLowerCase();
  const rows = portfolioReports().filter(report => {
    const matchesQuery = !query || `${report.title} ${report.funder} ${report.id}`.toLowerCase().includes(query);
    const matchesFilter = currentFilter === "all" || (currentFilter === "attention" && report.status === "attention") || (currentFilter === "progress" && ["preparing","draft"].includes(report.status)) || (currentFilter === "verified" && report.status === "verified");
    return matchesQuery && matchesFilter;
  });
  $("#allReportsTable").innerHTML = rows.map(report => `<tr class="clickable" data-report-id="${escapeHtml(report.id)}"><td><strong>${escapeHtml(report.title)}</strong><small>${escapeHtml(report.id)}</small></td><td>${escapeHtml(report.funder)}</td><td>${escapeHtml(report.period)}</td><td><div class="coverage-mini"><i><span style="width:${report.coverage}%"></span></i><b>${report.coverage}%</b></div></td><td><strong>${escapeHtml(report.due)}</strong><small>${escapeHtml(report.dueMeta)}</small></td><td><span class="status-pill ${report.status}">${statusLabel(report.status)}</span></td><td><button class="table-menu" aria-label="Open report"><svg viewBox="0 0 24 24"><path d="m9 18 6-6-6-6"/></svg></button></td></tr>`).join("") || `<tr><td colspan="7">No reports match this view.</td></tr>`;
}

function openReport(id) {
  if (id === awardId) {
    currentReportId = awardId;
    renderState(state);
    route("report");
    return;
  }
  const report = portfolioReports().find(item => item.id === id);
  if (!report) return;
  currentReportId = report.id;
  renderCustomReport(report);
  route("report");
}

function renderCustomReport(report) {
  $("#reportTitle").textContent = report.title;
  $("#reportSubtitle").textContent = `Reporting workspace · ${report.period}`;
  $(".report-id").textContent = report.id;
  const pill = $("#reportStatusPill"); pill.className = `status-pill ${report.status}`; pill.textContent = statusLabel(report.status);
  $("#resetButton").classList.add("hidden");
  $("#editClaimsButton").classList.add("hidden");
  $("#runButton").disabled = true; $("span", $("#runButton")).textContent = report.evidence ? "Evidence indexing" : "Add evidence to audit";
  $("#coverageMetric").textContent = "0 of 3"; $("#coverageBar").style.width = "0%";
  $("#evidenceMetric").textContent = report.evidence; $("#evidenceTabCount").textContent = report.evidence;
  $("#evidenceMetric").nextElementSibling.textContent = report.evidence ? "Files awaiting classification" : "No evidence added yet";
  $("#statusTitle").textContent = "Draft workspace"; $("#integritySubtext").textContent = "Claims not audited yet";
  if (report.status === "verified") {
    $("#coverageMetric").textContent = "3 of 3"; $("#coverageBar").style.width = "100%";
    $("#statusTitle").textContent = "Verified"; $("#integritySubtext").textContent = "Zero unsupported claims";
    $("span", $("#runButton")).textContent = "Audit complete";
  }
  const dueCard = $$(".summary-card")[0]; $("strong", dueCard).textContent = report.due; $("p", dueCard).textContent = "Reporting deadline";
  $("#findingsArea").classList.add("hidden"); $("#emptyState").classList.remove("hidden");
  $("#emptyState h3").textContent = report.evidence ? "Evidence is being indexed" : "Add evidence to complete this workspace";
  $("#emptyState p").textContent = report.evidence ? `${report.evidence} uploaded file${report.evidence === 1 ? " is" : "s are"} being classified and mapped to the report claims.` : "The report structure and draft claims are saved. Upload supporting files before running the evidence audit.";
  if (report.status === "verified") {
    $("#emptyState h3").textContent = "Evidence audit complete";
    $("#emptyState p").textContent = `${report.evidence} source artifacts support every material claim in this reporting period.`;
  }
  $("#emptyState [data-run-audit]").disabled = true; $("#emptyState [data-run-audit]").textContent = report.evidence ? "Indexing evidence" : "Upload evidence first";
  $(".report-side").classList.add("hidden"); $(".report-workspace-grid").style.gridTemplateColumns = "1fr";
  $("#claimsGrid").innerHTML = `<article class="claim-card"><div><small>DRAFT · FINANCIAL</small><strong>Eligible expenses claimed</strong><p>Entered during report creation</p></div><div><small>Claimed value</small><strong>${money(report.claims?.expenses || 0)}</strong></div><div class="claim-evidence"><small>Linked evidence</small><span>${report.evidence} files</span></div></article><article class="claim-card"><div><small>DRAFT · OUTCOME</small><strong>People served</strong><p>${escapeHtml(report.claims?.narrative || "No outcome summary entered")}</p></div><div><small>Claimed value</small><strong>${Number(report.claims?.people || 0).toLocaleString()} people</strong></div><div class="claim-evidence"><small>Linked evidence</small><span>Pending match</span></div></article>`;
  $("#evidenceTable").innerHTML = report.files?.length ? report.files.map((filename,index) => `<tr><td><strong>${escapeHtml(filename)}</strong><small>UPLOAD-${index + 1} · Awaiting server hash</small></td><td>${humanKind(fileKind(filename))}</td><td>—</td><td>Today</td><td><span class="status-pill draft">Indexing</span></td></tr>`).join("") : `<tr><td colspan="5">No evidence uploaded. Use the evidence library to add files.</td></tr>`;
  $("#trailEmpty").classList.remove("hidden"); $("#eventTrail").innerHTML = "";
}

function renderEvidence() {
  if (!state) return;
  $("#evidenceTabCount").textContent = state.evidence.length;
  $("#evidenceMetric").textContent = state.evidence.length;
  $("#evidenceTable").innerHTML = state.evidence.map(item => {
    let value = "—";
    if (item.amount != null) value = money(item.amount);
    else if (item.participant_ids?.length) value = `${item.participant_ids.length} people`;
    const shownStatus = state.status === "verified" && item.status === "included" ? "verified" : item.status;
    return `<tr><td><strong>${escapeHtml(item.filename)}</strong><small>${escapeHtml(item.id)} · ${escapeHtml(item.sha256.slice(0,12))}…</small></td><td>${humanKind(item.kind)}</td><td>${value}</td><td>${formatDate(item.captured_on)}</td><td><span class="status-pill ${shownStatus === "excluded" ? "attention" : shownStatus === "verified" ? "verified" : "draft"}">${humanKind(shownStatus)}</span></td></tr>`;
  }).join("");
  const recent = [...state.evidence].reverse();
  $("#libraryTable").innerHTML = recent.map(item => `<tr><td><div class="library-file"><span class="file-icon">${escapeHtml(item.filename.split(".").pop().slice(0,4).toUpperCase())}</span><div><strong>${escapeHtml(item.filename)}</strong><small>${escapeHtml(item.sha256.slice(0,12))}…</small></div></div></td><td><strong>Community Youth Access</strong><small>Q3 2026</small></td><td>${escapeHtml(item.source_ref.split(" · ")[0])}</td><td>${formatDate(item.captured_on)}</td><td><span class="status-pill ${item.status === "excluded" ? "attention" : "verified"}">${item.status === "excluded" ? "Flagged" : "Hash verified"}</span></td></tr>`).join("");
  $("#artifactMetric").textContent = 142 + state.evidence.length;
}

function renderClaims() {
  if (!state) return;
  $("#claimsGrid").innerHTML = state.claims.map(claim => `<article class="claim-card"><div><small>${escapeHtml(claim.id)} · ${escapeHtml(claim.requirement_id)}</small><strong>${escapeHtml(claim.statement)}</strong><p>Draft value entered by the reporting team</p></div><div><small>Claimed value</small><strong>${claim.unit === "USD" ? money(claim.claimed_value) : `${Number(claim.claimed_value).toLocaleString()} ${escapeHtml(claim.unit)}`}</strong></div><div class="claim-evidence"><small>Linked evidence</small>${claim.evidence_ids.map(id => `<span>${escapeHtml(id)}</span>`).join(" ")}</div></article>`).join("");
  $("#claimExpensesInput").value = state.claims.find(claim => claim.id === "CLM-01")?.claimed_value ?? 0;
  $("#claimYouthInput").value = state.claims.find(claim => claim.id === "CLM-02")?.claimed_value ?? 0;
}

function renderFindings() {
  const started = state.status !== "ready";
  $("#emptyState").classList.toggle("hidden", started);
  $("#findingsArea").classList.toggle("hidden", !started);
  $("#findingCount").textContent = state.findings.length;
  $("#findingsLabel").textContent = state.status === "verified" ? "Resolved findings" : "Blocking findings";
  $("#findingSubtitle").textContent = state.status === "verified" ? "Fresh verification passed after the approved correction." : "The report cannot be defended as written.";
  $("#findingsList").innerHTML = state.findings.map((finding, index) => `<article class="finding" style="animation-delay:${index * 55}ms"><div class="finding-index">${state.status === "verified" ? "✓" : String(index + 1).padStart(2,"0")}</div><div><h4>${escapeHtml(finding.title)}</h4><p>${escapeHtml(finding.detail)}</p><div class="finding-evidence">${finding.evidence_ids.map(id => `<span>${escapeHtml(id)}</span>`).join("")}</div></div><div class="finding-values">${finding.observed ? `<div><small>Observed</small><strong class="bad">${escapeHtml(finding.observed)}</strong></div>` : ""}${finding.expected ? `<div><small>Expected</small><strong>${escapeHtml(finding.expected)}</strong></div>` : ""}</div></article>`).join("") + (state.status === "blocked" ? `<button class="primary-button inline" data-review-decision style="margin:18px 12px 4px">Review correction plan</button>` : "");
}

function renderTrail() {
  $("#trailEmpty").classList.toggle("hidden", state.events.length > 0);
  $("#eventTrail").innerHTML = state.events.map(event => `<li><strong>${escapeHtml(event.title)}</strong><p>${escapeHtml(event.detail)}</p><code>${escapeHtml(event.tool)}</code></li>`).join("");
}

function renderDecision() {
  const decision = state.decision;
  const approve = $("#approveButton");
  const reject = $("#keepBlockedButton");
  if (decision && state.status === "blocked") {
    $("#decisionTitle").textContent = decision.title;
    $("#decisionSummary").textContent = decision.summary;
    $("#decisionRecommendation").textContent = decision.recommendation;
    $("#decisionConsequences").innerHTML = decision.consequences.map(item => `<li>${escapeHtml(item)}</li>`).join("");
    $("#approveLabel").textContent = decision.action_label;
    const pending = decision.status === "pending";
    approve.disabled = !pending; reject.disabled = !pending;
  } else if (state.status === "verified") {
    $("#decisionTitle").textContent = "Correction approved and independently re-verified";
    $("#decisionSummary").textContent = "Every material claim is now traceable to eligible evidence. The packet is ready for authorized human review.";
    $("#decisionRecommendation").textContent = "Open the verified packet, complete the funder narrative, and submit through the authorized human workflow.";
    $("#decisionConsequences").innerHTML = `<li>Eligible expenses verified at $480.00.</li><li>92 unique youth supported across three attendance logs.</li><li>Original exclusions remain visible in the audit trail.</li>`;
    approve.disabled = true; reject.disabled = true;
  } else {
    approve.disabled = true; reject.disabled = true;
  }
  const openDecisions = state.status === "blocked" && decision?.status === "pending" ? 1 : 0;
  $(".decision-queue .surface-head p").textContent = `${openDecisions} open · oldest first`;
  $(".queue-item").classList.toggle("hidden", openDecisions === 0);
  $(".queue-item i").textContent = `${state.findings.length} findings`;
  const activityCopy = $(".activity-avatar.alert")?.nextElementSibling;
  if (activityCopy) {
    $("strong", activityCopy).textContent = openDecisions ? "One decision requested" : "Evidence preparation started";
  }
  $("#decisionNavCount").textContent = openDecisions;
  $("#decisionNavCount").classList.toggle("hidden", openDecisions === 0);
  $("#attentionMetric").textContent = openDecisions;
}

function renderState(nextState) {
  state = nextState;
  if (currentReportId !== awardId) return;
  $("#reportTitle").textContent = "Community Youth Access Grant";
  $("#reportSubtitle").textContent = "Quarterly performance report · Jul 1–Sep 30, 2026";
  $(".report-id").textContent = awardId;
  $("#resetButton").classList.remove("hidden");
  $("#editClaimsButton").classList.remove("hidden");
  $("#evidenceMetric").nextElementSibling.textContent = "2 financial · 3 program";
  $(".report-side").classList.remove("hidden"); $(".report-workspace-grid").style.gridTemplateColumns = "";
  const dueCard = $$(".summary-card")[0]; $("strong", dueCard).textContent = "Oct 15, 2026"; $("p", dueCard).textContent = "31 days remaining";
  $("#emptyState h3").textContent = "Ready for an evidence audit";
  $("#emptyState p").textContent = "Proofline will interpret the award terms, reconcile both report claims, detect gaps, and pause only where human authority is required.";
  $("#emptyState [data-run-audit]").disabled = false; $("#emptyState [data-run-audit]").textContent = "Run evidence audit";
  const covered = Number(state.metrics.requirements_covered);
  const total = Number(state.metrics.total_requirements);
  const percent = Math.round((covered / (total || 1)) * 100);
  $("#coverageMetric").textContent = `${covered} of ${total}`;
  $("#coverageBar").style.width = `${percent}%`;
  $("#agentMode").textContent = state.agent_mode === "agentcore" ? "Live AgentCore loop" : state.agent_mode === "strands" ? "Live Bedrock loop" : "Deterministic product twin";
  const status = state.status;
  $("#statusTitle").textContent = status === "ready" ? "Ready to audit" : status === "blocked" ? "Needs attention" : status === "verified" ? "Verified" : "Audit in progress";
  $("#integritySubtext").textContent = status === "ready" ? "No checks run yet" : status === "blocked" ? `${state.metrics.blockers} material blockers` : "Zero unsupported claims";
  const pill = $("#reportStatusPill");
  pill.className = `status-pill ${status === "blocked" ? "attention" : status === "verified" ? "verified" : "preparing"}`;
  pill.textContent = status === "blocked" ? "Needs attention" : status === "verified" ? "Verified" : "Preparing";
  const runButton = $("#runButton");
  runButton.disabled = status !== "ready";
  $("span", runButton).textContent = status === "ready" ? "Run evidence audit" : status === "blocked" ? "Audit paused" : "Audit complete";
  renderEvidence(); renderClaims(); renderFindings(); renderTrail(); renderDecision(); renderPortfolio();
}

async function load() { renderState(await api("/api/state")); }
async function runAudit() {
  if (state?.status !== "ready") return;
  const button = $("#runButton"); button.disabled = true; $("span", button).textContent = "Inspecting evidence…";
  try {
    await api(`/api/audits/${awardId}/run`, {method:"POST"});
    await load(); route("report");
    showToast("Audit paused safely. One correction plan needs human approval.");
  } catch (error) { showToast(error.message); button.disabled = false; $("span", button).textContent = "Run evidence audit"; }
}
async function resolveDecision(approve) {
  if (!state?.decision) return;
  try {
    await api(`/api/audits/${awardId}/resolve`, {method:"POST", body:JSON.stringify({decision_id:state.decision.id, approve})});
    await load();
    showToast(approve ? "Correction approved. Fresh verification passed." : "Report remains blocked. No records were changed.");
  } catch (error) { showToast(error.message); }
}

function openModal(id) { $(id).classList.remove("hidden"); document.body.style.overflow = "hidden"; }
function closeModal(modal) { modal.classList.add("hidden"); document.body.style.overflow = ""; }
function showFiles(input, target) {
  const files = [...input.files];
  $(target).innerHTML = files.length ? files.map(file => `<span class="file-token">${escapeHtml(file.name)} · ${Math.max(1, Math.round(file.size / 1024))} KB</span>`).join("") : "<span>No files selected yet</span>";
}
function setIntakeStep(step) {
  intakeStep = step;
  $$(".form-step", $("#intakeModal")).forEach(panel => panel.classList.toggle("active", Number(panel.dataset.step) === step));
  $$(".stepper i", $("#intakeModal")).forEach((item, index) => item.classList.toggle("active", index < step));
  $("#stepKicker").textContent = `Step ${step} of 3`;
  $("#intakeBack").classList.toggle("hidden", step === 1);
  $("#intakeNext").textContent = step === 3 ? "Create report" : "Continue";
}
function validateStep(step) {
  const fields = step === 1 ? [$("#intakeAward"),$("#intakeStart"),$("#intakeEnd"),$("#intakeDue")] : [$("#intakeExpenses"),$("#intakePeople")];
  const invalid = fields.find(field => !field.checkValidity());
  if (invalid) { invalid.reportValidity(); return false; }
  return true;
}
function createReport() {
  const award = $("#intakeAward").value;
  const report = {
    id:`RPT-${Date.now().toString().slice(-6)}`, title:award, funder:"New reporting workspace", period:`${formatDate($("#intakeStart").value)}–${formatDate($("#intakeEnd").value)}`,
    shortPeriod:"New", due:formatDate($("#intakeDue").value).replace(", 2026",""), dueMeta:"New", coverage:0, status:"draft", evidence:$("#intakeFiles").files.length,
    claims:{expenses:Number($("#intakeExpenses").value), people:Number($("#intakePeople").value), narrative:$("#intakeNarrative").value}, files:[...$("#intakeFiles").files].map(file => file.name),
  };
  customReports.unshift(report); localStorage.setItem(customReportsKey, JSON.stringify(customReports));
  renderPortfolio(); closeModal($("#intakeModal")); $("#intakeForm").reset(); setIntakeStep(1); route("reports");
  showToast(`${award} report created with ${report.evidence} evidence file${report.evidence === 1 ? "" : "s"}.`);
}

async function hashFile(file) {
  const digest = await crypto.subtle.digest("SHA-256", await file.arrayBuffer());
  return [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2,"0")).join("");
}
function fileKind(filename) {
  const extension = filename.split(".").pop().toLowerCase();
  return ({pdf:"pdf",csv:"attendance_log",xlsx:"spreadsheet",xls:"spreadsheet",jpg:"image",jpeg:"image",png:"image",txt:"supporting_document",docx:"document"})[extension] || "supporting_document";
}
async function uploadEvidence() {
  const files = [...$("#uploadFiles").files];
  if (!files.length) { showToast("Choose at least one evidence file first."); return; }
  const submit = $("#uploadSubmit"); submit.disabled = true; submit.textContent = "Hashing & uploading…";
  try {
    for (const file of files) {
      await api(`/api/reports/${awardId}/evidence`, {method:"POST", body:JSON.stringify({filename:file.name, kind:fileKind(file.name), captured_on:new Date().toISOString().slice(0,10), sha256:await hashFile(file), size_bytes:file.size})});
    }
    await load(); closeModal($("#uploadModal")); $("#uploadFiles").value = ""; showFiles($("#uploadFiles"), "#uploadFileList");
    showToast(`${files.length} evidence file${files.length === 1 ? "" : "s"} hashed and added to the report.`);
  } catch (error) { showToast(error.message); }
  finally { submit.disabled = false; submit.textContent = "Upload files"; }
}

async function saveClaims() {
  try {
    const next = await api(`/api/reports/${awardId}/claims`, {method:"PATCH", body:JSON.stringify({eligible_expenses:Number($("#claimExpensesInput").value), people_served:Number($("#claimYouthInput").value)})});
    renderState(next); closeModal($("#editClaimsModal")); showToast("Draft claims saved. They will be tested in the next audit.");
  } catch (error) { showToast(error.message); }
}

document.addEventListener("click", event => {
  const routeTarget = event.target.closest("[data-route]");
  if (routeTarget) { event.preventDefault(); route(routeTarget.dataset.route); }
  const reportTarget = event.target.closest("[data-report-id]");
  if (reportTarget) openReport(reportTarget.dataset.reportId);
  if (event.target.closest("[data-open-intake]")) { setIntakeStep(1); openModal("#intakeModal"); }
  if (event.target.closest("[data-open-upload]")) openModal("#uploadModal");
  if (event.target.closest("[data-close-modal]")) closeModal(event.target.closest(".modal-backdrop"));
  if (event.target.closest("[data-run-audit]")) runAudit();
  if (event.target.closest("[data-review-decision]")) route("decisions");
  if (event.target.closest("[data-open-current-report]")) route("report");
});

$("#runButton").addEventListener("click", runAudit);
$("#approveButton").addEventListener("click", () => resolveDecision(true));
$("#keepBlockedButton").addEventListener("click", () => resolveDecision(false));
$("#resetButton").addEventListener("click", async () => { try { renderState(await api("/api/reset", {method:"POST"})); showToast("Report restored to its original draft evidence."); } catch (error) { showToast(error.message); } });
$("#mobileMenu").addEventListener("click", () => $("#sidebar").classList.toggle("open"));
$("#reportSearch").addEventListener("input", renderReportTable);
$(".search input").addEventListener("keydown", event => {
  if (event.key !== "Enter") return;
  $("#reportSearch").value = event.target.value;
  route("reports"); renderReportTable();
});
$$('#page-reports .segmented button').forEach((button, index) => button.addEventListener("click", () => { $$('#page-reports .segmented button').forEach(item => item.classList.remove("active")); button.classList.add("active"); currentFilter = ["all","attention","progress","verified"][index]; renderReportTable(); }));
$$('.tabs button').forEach(button => button.addEventListener("click", () => { $$('.tabs button').forEach(item => item.classList.remove("active")); button.classList.add("active"); $$('.tab-panel').forEach(panel => panel.classList.toggle("active", panel.dataset.tabPanel === button.dataset.tab)); }));
$("#intakeBack").addEventListener("click", event => { event.preventDefault(); setIntakeStep(Math.max(1, intakeStep - 1)); });
$("#intakeNext").addEventListener("click", event => { event.preventDefault(); if (intakeStep < 3) { if (validateStep(intakeStep)) setIntakeStep(intakeStep + 1); } else createReport(); });
$("#intakeFiles").addEventListener("change", event => showFiles(event.target, "#intakeFileList"));
$("#uploadFiles").addEventListener("change", event => showFiles(event.target, "#uploadFileList"));
$("#uploadSubmit").addEventListener("click", uploadEvidence);
$("#editClaimsButton").addEventListener("click", () => openModal("#editClaimsModal"));
$("#saveClaimsButton").addEventListener("click", saveClaims);
$("#saveSettings").addEventListener("click", () => { localStorage.setItem("proofline-policy-saved", new Date().toISOString()); showToast("Evidence policy saved for future audit runs."); });
$$('.connect-integration').forEach(button => button.addEventListener("click", () => showToast("Connection setup opened. Authentication would continue with the provider.")));
$$('.manage-integration').forEach(button => button.addEventListener("click", () => showToast("Integration settings are ready to manage.")));
window.addEventListener("keydown", event => { if (event.key === "Escape") $$(".modal-backdrop:not(.hidden)").forEach(closeModal); });

renderPortfolio();
route(routeLabels[location.hash.slice(1)] ? location.hash.slice(1) : "dashboard", false);
load().catch(error => showToast(error.message));
