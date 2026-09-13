from __future__ import annotations

import os
from collections import OrderedDict
from pathlib import Path
from threading import Lock
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from mangum import Mangum

from .agentcore_client import run_agentcore_audit
from .models import AuditRun, AuditStatus, DashboardState, ResolutionRun, ResolveRequest
from .packet import render_packet
from .store import GrantStore, store
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

_MAX_PUBLIC_SESSIONS = 200
_session_stores: OrderedDict[str, GrantStore] = OrderedDict()
_session_lock = Lock()


def _store_for(session_id: str | None) -> GrantStore:
    """Give each public browser an isolated, bounded in-memory demo scenario."""
    if not session_id:
        return store
    key = session_id.strip()[:128]
    if not key:
        return store
    with _session_lock:
        grant_store = _session_stores.get(key)
        if grant_store is None:
            if len(_session_stores) >= _MAX_PUBLIC_SESSIONS:
                _session_stores.popitem(last=False)
            grant_store = GrantStore()
            _session_stores[key] = grant_store
        else:
            _session_stores.move_to_end(key)
    return grant_store


@app.get("/", include_in_schema=False)
def index() -> HTMLResponse:
    return HTMLResponse((STATIC / "index.html").read_text())


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "proofline", "agent": describe_agent()}


def dashboard_state(grant_store: GrantStore = store) -> DashboardState:
    blocker_count = len([item for item in grant_store.findings if not item.resolved])
    included = [
        item for item in grant_store.evidence.values() if item.status.value == "included"
    ]
    if grant_store.status == AuditStatus.VERIFIED:
        supported_claims = len(grant_store.claims)
        requirements_covered = len(grant_store.requirements)
    elif grant_store.status == AuditStatus.BLOCKED:
        supported_claims = 0
        requirements_covered = 1
    else:
        supported_claims = 0
        requirements_covered = 0
    return DashboardState(
        award=grant_store.award,
        status=grant_store.status,
        requirements=grant_store.requirements,
        evidence=list(grant_store.evidence.values()),
        claims=list(grant_store.claims.values()),
        findings=grant_store.findings,
        events=grant_store.events[-30:],
        decision=grant_store.decision,
        metrics={
            "blockers": blocker_count,
            "evidence_files": len(grant_store.evidence),
            "included_evidence": len(included),
            "supported_claims": supported_claims,
            "total_claims": len(grant_store.claims),
            "requirements_covered": requirements_covered,
            "total_requirements": len(grant_store.requirements),
            "unsupported_material_claims": blocker_count,
            "submitted": False,
        },
        packet_ready=grant_store.packet_ready,
        agent_mode=grant_store.agent_mode,
    )


@app.get("/api/state", response_model=DashboardState)
def state(
    session_id: Annotated[str | None, Header(alias="X-Proofline-Session")] = None,
) -> DashboardState:
    return dashboard_state(_store_for(session_id))


@app.post("/api/audits/{award_id}/run", response_model=AuditRun)
def run_audit(
    award_id: str,
    session_id: Annotated[str | None, Header(alias="X-Proofline-Session")] = None,
) -> AuditRun:
    grant_store = _store_for(session_id)
    if award_id != grant_store.award.id:
        raise HTTPException(status_code=404, detail="Award not found")
    if grant_store.status != AuditStatus.READY:
        raise HTTPException(
            status_code=409, detail="Reset the scenario before starting another audit"
        )
    mode = os.getenv("PROOFLINE_AGENT_MODE", "deterministic").lower()
    if mode == "agentcore":
        return run_agentcore_audit(grant_store)
    if mode == "strands":
        return run_strands_audit(grant_store)
    grant_store.agent_mode = "deterministic"
    return DeterministicWorkflow(grant_store).audit()


@app.post("/api/audits/{award_id}/resolve", response_model=ResolutionRun)
def resolve(
    award_id: str,
    request: ResolveRequest,
    session_id: Annotated[str | None, Header(alias="X-Proofline-Session")] = None,
) -> ResolutionRun:
    grant_store = _store_for(session_id)
    if award_id != grant_store.award.id:
        raise HTTPException(status_code=404, detail="Award not found")
    try:
        return DeterministicWorkflow(grant_store).resolve(request.decision_id, request.approve)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.get("/api/reports/{award_id}/packet")
def packet(
    award_id: str,
    session_id: Annotated[str | None, Header(alias="X-Proofline-Session")] = None,
) -> Response:
    grant_store = _store_for(session_id)
    if award_id != grant_store.award.id:
        raise HTTPException(status_code=404, detail="Award not found")
    try:
        content = render_packet(grant_store)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return Response(
        content=content,
        media_type="text/html",
        headers={"Content-Disposition": f'inline; filename="{award_id}-verified-packet.html"'},
    )


@app.post("/api/reset", response_model=DashboardState)
def reset(
    session_id: Annotated[str | None, Header(alias="X-Proofline-Session")] = None,
) -> DashboardState:
    grant_store = _store_for(session_id)
    grant_store.reset()
    return dashboard_state(grant_store)


handler = Mangum(app)
