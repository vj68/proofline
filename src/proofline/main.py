from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from mangum import Mangum

from .models import AuditRun, AuditStatus, DashboardState, ResolutionRun, ResolveRequest
from .packet import render_packet
from .store import store
from .strands_agent import describe_agent, run_strands_audit
from .workflow import DeterministicWorkflow

ROOT = Path(__file__).parent
STATIC = ROOT / "static"

app = FastAPI(
    title="Proofline",
    description="Evidence-first grant reporting for small nonprofits, powered by Strands Agents.",
    version="0.1.0",
)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
def index() -> HTMLResponse:
    return HTMLResponse((STATIC / "index.html").read_text())


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "proofline", "agent": describe_agent()}


def dashboard_state() -> DashboardState:
    blocker_count = len([item for item in store.findings if not item.resolved])
    included = [item for item in store.evidence.values() if item.status.value == "included"]
    if store.status == AuditStatus.VERIFIED:
        supported_claims = len(store.claims)
        requirements_covered = len(store.requirements)
    elif store.status == AuditStatus.BLOCKED:
        supported_claims = 0
        requirements_covered = 1
    else:
        supported_claims = 0
        requirements_covered = 0
    return DashboardState(
        award=store.award,
        status=store.status,
        requirements=store.requirements,
        evidence=list(store.evidence.values()),
        claims=list(store.claims.values()),
        findings=store.findings,
        events=store.events[-30:],
        decision=store.decision,
        metrics={
            "blockers": blocker_count,
            "evidence_files": len(store.evidence),
            "included_evidence": len(included),
            "supported_claims": supported_claims,
            "total_claims": len(store.claims),
            "requirements_covered": requirements_covered,
            "total_requirements": len(store.requirements),
            "unsupported_material_claims": blocker_count,
            "submitted": False,
        },
        packet_ready=store.packet_ready,
        agent_mode=store.agent_mode,
    )


@app.get("/api/state", response_model=DashboardState)
def state() -> DashboardState:
    return dashboard_state()


@app.post("/api/audits/{award_id}/run", response_model=AuditRun)
def run_audit(award_id: str) -> AuditRun:
    if award_id != store.award.id:
        raise HTTPException(status_code=404, detail="Award not found")
    if store.status != AuditStatus.READY:
        raise HTTPException(
            status_code=409, detail="Reset the scenario before starting another audit"
        )
    mode = os.getenv("PROOFLINE_AGENT_MODE", "deterministic").lower()
    if mode == "strands":
        return run_strands_audit(store)
    store.agent_mode = "deterministic"
    return DeterministicWorkflow(store).audit()


@app.post("/api/audits/{award_id}/resolve", response_model=ResolutionRun)
def resolve(award_id: str, request: ResolveRequest) -> ResolutionRun:
    if award_id != store.award.id:
        raise HTTPException(status_code=404, detail="Award not found")
    try:
        return DeterministicWorkflow(store).resolve(request.decision_id, request.approve)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.get("/api/reports/{award_id}/packet")
def packet(award_id: str) -> Response:
    if award_id != store.award.id:
        raise HTTPException(status_code=404, detail="Award not found")
    try:
        content = render_packet(store)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return Response(
        content=content,
        media_type="text/html",
        headers={"Content-Disposition": f'inline; filename="{award_id}-verified-packet.html"'},
    )


@app.post("/api/reset", response_model=DashboardState)
def reset() -> DashboardState:
    store.reset()
    return dashboard_state()


handler = Mangum(app)
