from __future__ import annotations

import csv
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

from .models import (
    AuditEvent,
    AuditStatus,
    Award,
    Claim,
    DecisionCard,
    Evidence,
    EvidenceStatus,
    Finding,
    Requirement,
)

FIXTURES = Path(__file__).parent / "fixtures"


def fixture_hash(filename: str) -> str:
    return sha256((FIXTURES / filename).read_bytes()).hexdigest()


def fixture_participants(filename: str) -> list[str]:
    with (FIXTURES / filename).open(newline="") as handle:
        return [
            row["participant_id"]
            for row in csv.DictReader(handle)
            if row["eligible_workshop"].lower() == "true"
        ]


AWARD = Award(
    id="CYA-2026-017",
    program="Community Youth Access Grant",
    recipient="Harbor Light Youth Collective",
    award_amount=25_000,
    reporting_start="2026-07-01",
    reporting_end="2026-09-30",
    report_due="2026-10-15",
    source_filename="award-and-reporting-terms.md",
    source_sha256=fixture_hash("award-and-reporting-terms.md"),
)

REQUIREMENTS = [
    Requirement(
        id="REQ-01",
        category="financial",
        description="Report eligible program expenses incurred from July 1 through September 30, 2026.",
        source_ref="Award terms · page 4 · §7.1",
        unit="USD",
    ),
    Requirement(
        id="REQ-02",
        category="outcome",
        description="Report the number of unique youth who attended an eligible workshop during the quarter.",
        source_ref="Performance schedule · page 6 · Metric YOUTH-01",
        unit="youth",
    ),
    Requirement(
        id="REQ-03",
        category="evidence",
        description="Retain invoices, receipts, and attendance records supporting every reported figure.",
        source_ref="Award terms · page 5 · §8.3",
    ),
]

EVIDENCE = [
    Evidence(
        id="E-101",
        filename="receipt_art_supplies_0904.txt",
        kind="receipt",
        captured_on="2026-09-04",
        source_ref="Evidence inbox · finance/receipt_art_supplies_0904.txt",
        sha256=fixture_hash("receipt_art_supplies_0904.txt"),
        amount=480,
        budget_category="Program supplies",
        note="Art supplies for September workshops.",
    ),
    Evidence(
        id="E-102",
        filename="receipt_art_supplies_0904_copy.txt",
        kind="receipt",
        captured_on="2026-09-04",
        source_ref="Evidence inbox · uploads/receipt_art_supplies_0904_copy.txt",
        sha256=fixture_hash("receipt_art_supplies_0904_copy.txt"),
        amount=480,
        budget_category="Program supplies",
        note="Duplicate upload of E-101.",
    ),
    Evidence(
        id="E-201",
        filename="transport_invoice_1002.txt",
        kind="invoice",
        captured_on="2026-10-02",
        source_ref="Evidence inbox · finance/transport_invoice_1002.txt",
        sha256=fixture_hash("transport_invoice_1002.txt"),
        amount=350,
        budget_category="Participant transport",
        note="Valid expense, but belongs to the next reporting period.",
    ),
    Evidence(
        id="E-301",
        filename="attendance_july.csv",
        kind="attendance_log",
        captured_on="2026-07-31",
        source_ref="Evidence inbox · programs/attendance_july.csv",
        sha256=fixture_hash("attendance_july.csv"),
        metric="unique_youth",
        metric_value=28,
        participant_ids=fixture_participants("attendance_july.csv"),
        note="De-identified participant IDs; July workshops.",
    ),
    Evidence(
        id="E-302",
        filename="attendance_august.csv",
        kind="attendance_log",
        captured_on="2026-08-31",
        source_ref="Evidence inbox · programs/attendance_august.csv",
        sha256=fixture_hash("attendance_august.csv"),
        metric="unique_youth",
        metric_value=31,
        participant_ids=fixture_participants("attendance_august.csv"),
        note="De-identified participant IDs; August workshops.",
    ),
]

MISSING_SEPTEMBER_EVIDENCE = Evidence(
    id="E-303",
    filename="attendance_september.csv",
    kind="attendance_log",
    captured_on="2026-09-30",
    source_ref="Program lead response · programs/attendance_september.csv",
    sha256=fixture_hash("attendance_september.csv"),
    metric="unique_youth",
    metric_value=33,
    participant_ids=fixture_participants("attendance_september.csv"),
    note="De-identified participant IDs; September workshops. Added after human review.",
)

CLAIMS = [
    Claim(
        id="CLM-01",
        requirement_id="REQ-01",
        statement="Eligible expenses incurred during the reporting period",
        claimed_value=1_310,
        unit="USD",
        evidence_ids=["E-101", "E-102", "E-201"],
    ),
    Claim(
        id="CLM-02",
        requirement_id="REQ-02",
        statement="Unique youth attending an eligible workshop",
        claimed_value=92,
        unit="youth",
        evidence_ids=["E-301", "E-302"],
    ),
]


class GrantStore:
    """In-memory state for a reproducible, privacy-safe competition scenario."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.award = AWARD.model_copy(deep=True)
        self.requirements = deepcopy(REQUIREMENTS)
        self.evidence = {item.id: item for item in deepcopy(EVIDENCE)}
        self.claims = {item.id: item for item in deepcopy(CLAIMS)}
        self.findings: list[Finding] = []
        self.events: list[AuditEvent] = []
        self.decision: DecisionCard | None = None
        self.status = AuditStatus.READY
        self.packet_ready = False
        self.agent_mode = "deterministic"
        self._event_id = 0

    def event(
        self, kind: str, title: str, detail: str, tool: str, **metadata: object
    ) -> AuditEvent:
        self._event_id += 1
        item = AuditEvent(
            id=self._event_id,
            kind=kind,
            title=title,
            detail=detail,
            tool=tool,
            metadata=dict(metadata),
        )
        self.events.append(item)
        return item

    def apply_approved_correction(self) -> int:
        """Apply the bounded resolution represented by the demo decision card."""
        if not self.decision or self.decision.status != "pending":
            return 0
        self.evidence["E-102"].status = EvidenceStatus.EXCLUDED
        self.evidence["E-201"].status = EvidenceStatus.EXCLUDED
        self.evidence[MISSING_SEPTEMBER_EVIDENCE.id] = MISSING_SEPTEMBER_EVIDENCE.model_copy(
            deep=True
        )
        self.claims["CLM-01"].claimed_value = 480
        self.claims["CLM-01"].evidence_ids = ["E-101"]
        self.claims["CLM-02"].evidence_ids = ["E-301", "E-302", "E-303"]
        self.decision.status = "approved"
        return 3

    def update_claims(self, eligible_expenses: float, people_served: int) -> None:
        """Persist user-entered draft claims before an audit starts."""
        if self.status != AuditStatus.READY:
            raise ValueError("Reset this report before editing claims after an audit")
        self.claims["CLM-01"].claimed_value = eligible_expenses
        self.claims["CLM-02"].claimed_value = people_served

    def add_uploaded_evidence(
        self, filename: str, kind: str, captured_on: str, digest: str, size_bytes: int
    ) -> Evidence:
        """Register browser-uploaded evidence with its client-computed content hash."""
        if self.status != AuditStatus.READY:
            raise ValueError("Reset this report before adding evidence after an audit")
        # Keep manual-upload IDs in a separate range from source-system evidence
        # (including the reserved E-303 September attendance artifact).
        numeric_ids = [
            int(key.split("-")[-1])
            for key in self.evidence
            if key.startswith("E-") and int(key.split("-")[-1]) >= 900
        ]
        evidence_id = f"E-{max(numeric_ids, default=899) + 1}"
        item = Evidence(
            id=evidence_id,
            filename=filename,
            kind=kind,
            captured_on=captured_on,
            source_ref=f"Manual upload · {filename}",
            sha256=digest,
            note=f"Uploaded by reporting team ({size_bytes} bytes).",
        )
        self.evidence[item.id] = item
        return item


store = GrantStore()
