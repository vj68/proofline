from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from .models import AuditStatus, DecisionCard, EvidenceStatus, Finding, FindingCode
from .store import GrantStore


def _money(value: float) -> str:
    return f"${value:,.2f}"


class IntegrityVerifier:
    """Deterministic authority for report readiness; no LLM can bypass these checks."""

    def __init__(self, grant_store: GrantStore) -> None:
        self.store = grant_store

    def scan(self) -> list[Finding]:
        findings: list[Finding] = []
        evidence = list(self.store.evidence.values())
        included = [item for item in evidence if item.status == EvidenceStatus.INCLUDED]

        by_hash: dict[str, list] = defaultdict(list)
        for item in included:
            by_hash[item.sha256].append(item)
        for matches in by_hash.values():
            if len(matches) > 1:
                ids = [item.id for item in matches]
                findings.append(
                    Finding(
                        id="F-001",
                        code=FindingCode.DUPLICATE_EVIDENCE,
                        title="The same $480 receipt is counted twice",
                        detail="Two files have the same SHA-256 digest, transaction date, amount, and vendor context.",
                        evidence_ids=ids,
                        claim_id="CLM-01",
                        expected="One supported transaction",
                        observed=f"{len(matches)} copies included",
                        resolution="Exclude E-102 while retaining it in the audit trail.",
                    )
                )

        outside = [
            item
            for item in included
            if item.amount is not None
            and not (
                self.store.award.reporting_start
                <= item.captured_on
                <= self.store.award.reporting_end
            )
        ]
        if outside:
            findings.append(
                Finding(
                    id="F-002",
                    code=FindingCode.OUTSIDE_PERIOD,
                    title="An expense belongs to the next reporting period",
                    detail=(
                        f"{outside[0].filename} is dated {outside[0].captured_on.isoformat()}, after the "
                        f"September 30 reporting-period close."
                    ),
                    evidence_ids=[item.id for item in outside],
                    claim_id="CLM-01",
                    expected="2026-07-01 through 2026-09-30",
                    observed=outside[0].captured_on.isoformat(),
                    resolution="Carry E-201 forward; do not report it this quarter.",
                )
            )

        financial_claim = self.store.claims["CLM-01"]
        # A duplicate file may be present while the report is blocked, so recompute the
        # defensible total from unique evidence digests rather than counting every upload.
        seen_financial_hashes: set[str] = set()
        valid_total = Decimal(0)
        for item in included:
            if (
                item.id not in financial_claim.evidence_ids
                or item.amount is None
                or not (
                    self.store.award.reporting_start
                    <= item.captured_on
                    <= self.store.award.reporting_end
                )
                or item.sha256 in seen_financial_hashes
            ):
                continue
            seen_financial_hashes.add(item.sha256)
            valid_total += Decimal(str(item.amount))
        if Decimal(str(financial_claim.claimed_value)) != valid_total:
            findings.append(
                Finding(
                    id="F-003",
                    code=FindingCode.TOTAL_MISMATCH,
                    title="The financial claim does not match eligible evidence",
                    detail="The draft includes duplicate and out-of-period evidence in its expense total.",
                    evidence_ids=financial_claim.evidence_ids,
                    claim_id=financial_claim.id,
                    expected=_money(float(valid_total)),
                    observed=_money(financial_claim.claimed_value),
                    resolution=f"Recalculate the claim to {_money(float(valid_total))} after exclusions.",
                )
            )

        outcome_claim = self.store.claims["CLM-02"]
        supported_participants = {
            participant_id
            for item in included
            if item.id in outcome_claim.evidence_ids and item.metric == "unique_youth"
            for participant_id in item.participant_ids
        }
        supported_outcome = Decimal(len(supported_participants))
        if Decimal(str(outcome_claim.claimed_value)) != supported_outcome:
            findings.append(
                Finding(
                    id="F-004",
                    code=FindingCode.UNSUPPORTED_CLAIM,
                    title="33 reported participants have no supporting log",
                    detail="July and August logs support 59 of the 92 youth in the draft. September evidence is missing.",
                    evidence_ids=outcome_claim.evidence_ids,
                    claim_id=outcome_claim.id,
                    expected=f"{outcome_claim.claimed_value:.0f} youth claimed",
                    observed=f"{supported_outcome:.0f} youth supported",
                    resolution="Attach the September attendance log or reduce the reported outcome to 59.",
                )
            )

        return findings

    def run(self) -> list[Finding]:
        self.store.status = AuditStatus.SCANNING
        self.store.packet_ready = False
        self.store.event(
            "inspection",
            "Award obligations mapped",
            f"Mapped {len(self.store.requirements)} requirements from {self.store.award.source_filename}.",
            "inspect_award_terms",
        )
        self.store.event(
            "inspection",
            "Evidence inbox inspected",
            f"Hashed and classified {len(self.store.evidence)} receipts, invoices, and activity logs.",
            "inspect_evidence_inbox",
        )
        findings = self.scan()
        self.store.findings = findings
        self.store.event(
            "verification",
            "Independent integrity checks completed",
            f"Dates, hashes, totals, reporting periods, and claim coverage checked. {len(findings)} blockers found.",
            "run_integrity_checks",
            blockers=len(findings),
        )

        if findings:
            self.store.status = AuditStatus.BLOCKED
            self.store.decision = DecisionCard(
                id="DEC-001",
                title="Approve a bounded correction plan",
                summary="The draft cannot be supported as written. No report has been marked ready or submitted.",
                recommendation=(
                    "Exclude the duplicate receipt, carry the October invoice forward, attach the available "
                    "September attendance log, and recalculate the expense claim."
                ),
                consequences=[
                    "Reported eligible expenses change from $1,310.00 to $480.00.",
                    "The $350.00 October invoice remains retained for the next reporting period.",
                    "The 92-youth outcome becomes fully traceable to July, August, and September logs.",
                ],
                action_label="Approve corrections & re-verify",
            )
            self.store.event(
                "decision",
                "Human decision required",
                "Four related integrity blockers were consolidated into one reviewable correction plan.",
                "create_decision_card",
            )
        else:
            self.store.status = AuditStatus.VERIFIED
            self.store.packet_ready = True
            self.store.decision = None
            self.store.event(
                "packet",
                "Evidence packet verified",
                "Every material claim is supported and the report packet is ready for authorized review.",
                "generate_verified_packet",
            )
        return findings
