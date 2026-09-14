from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class AuditStatus(StrEnum):
    READY = "ready"
    SCANNING = "scanning"
    BLOCKED = "blocked"
    VERIFIED = "verified"


class EvidenceStatus(StrEnum):
    INCLUDED = "included"
    EXCLUDED = "excluded"
    MISSING = "missing"


class FindingCode(StrEnum):
    DUPLICATE_EVIDENCE = "duplicate_evidence"
    OUTSIDE_PERIOD = "outside_reporting_period"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    TOTAL_MISMATCH = "total_mismatch"


class Requirement(BaseModel):
    id: str
    category: str
    description: str
    source_ref: str
    expected_value: float | None = None
    unit: str | None = None


class Evidence(BaseModel):
    id: str
    filename: str
    kind: str
    captured_on: date
    source_ref: str
    sha256: str
    status: EvidenceStatus = EvidenceStatus.INCLUDED
    amount: float | None = None
    budget_category: str | None = None
    metric: str | None = None
    metric_value: float | None = None
    participant_ids: list[str] = Field(default_factory=list)
    note: str = ""


class Claim(BaseModel):
    id: str
    requirement_id: str
    statement: str
    claimed_value: float
    unit: str
    evidence_ids: list[str] = Field(default_factory=list)


class Finding(BaseModel):
    id: str
    code: FindingCode
    severity: str = "blocking"
    title: str
    detail: str
    evidence_ids: list[str] = Field(default_factory=list)
    claim_id: str | None = None
    expected: str | None = None
    observed: str | None = None
    resolution: str | None = None
    resolved: bool = False


class AuditEvent(BaseModel):
    id: int
    kind: str
    title: str
    detail: str
    tool: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, object] = Field(default_factory=dict)


class DecisionCard(BaseModel):
    id: str
    title: str
    summary: str
    recommendation: str
    consequences: list[str]
    action_label: str
    status: str = "pending"


class Award(BaseModel):
    id: str
    program: str
    recipient: str
    award_amount: float
    reporting_start: date
    reporting_end: date
    report_due: date
    source_filename: str
    source_sha256: str


class DashboardState(BaseModel):
    award: Award
    status: AuditStatus
    requirements: list[Requirement]
    evidence: list[Evidence]
    claims: list[Claim]
    findings: list[Finding]
    events: list[AuditEvent]
    decision: DecisionCard | None = None
    metrics: dict[str, int | float | str | bool]
    packet_ready: bool = False
    agent_mode: str = "deterministic"


class AuditRun(BaseModel):
    status: AuditStatus
    outcome: str
    findings: list[Finding]
    events: list[AuditEvent]
    tool_calls: int
    agent_mode: str


class ResolveRequest(BaseModel):
    decision_id: str
    approve: bool


class UpdateClaimsRequest(BaseModel):
    eligible_expenses: float = Field(ge=0)
    people_served: int = Field(ge=0)


class EvidenceUploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    kind: str = Field(default="supporting_document", max_length=64)
    captured_on: date
    sha256: str = Field(min_length=64, max_length=64)
    size_bytes: int = Field(default=0, ge=0)


class ResolutionRun(BaseModel):
    status: AuditStatus
    outcome: str
    resolved_findings: int
    remaining_findings: int
    events: list[AuditEvent]
