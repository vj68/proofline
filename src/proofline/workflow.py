from __future__ import annotations

from copy import deepcopy

from .models import AuditRun, AuditStatus, ResolutionRun
from .store import GrantStore
from .verifier import IntegrityVerifier


class DeterministicWorkflow:
    """Reproducible product twin used by tests, evaluations, and the public demo fallback."""

    def __init__(self, grant_store: GrantStore) -> None:
        self.store = grant_store

    def audit(self) -> AuditRun:
        start = len(self.store.events)
        findings = IntegrityVerifier(self.store).run()
        return AuditRun(
            status=self.store.status,
            outcome=(
                f"Report blocked: {len(findings)} integrity findings require one human decision."
                if findings
                else "Report verified: every material claim has supporting evidence."
            ),
            findings=findings,
            events=self.store.events[start:],
            tool_calls=len(self.store.events[start:]),
            agent_mode="deterministic",
        )

    def resolve(self, decision_id: str, approve: bool) -> ResolutionRun:
        if not self.store.decision or self.store.decision.id != decision_id:
            raise ValueError("Decision is missing or no longer active")
        if not approve:
            self.store.decision.status = "rejected"
            self.store.event(
                "decision",
                "Correction plan rejected",
                "The report remains blocked; no evidence or claims were changed.",
                "record_human_decision",
            )
            return ResolutionRun(
                status=AuditStatus.BLOCKED,
                outcome="Report remains blocked. No correction was applied.",
                resolved_findings=0,
                remaining_findings=len(self.store.findings),
                events=[self.store.events[-1]],
            )

        start = len(self.store.events)
        previous = len(self.store.findings)
        previous_findings = deepcopy(self.store.findings)
        changed = self.store.apply_approved_correction()
        self.store.event(
            "decision",
            "Bounded correction approved",
            f"Applied {changed} explicitly listed evidence changes; original records remain in the audit trail.",
            "record_human_decision",
        )
        remaining = IntegrityVerifier(self.store).run()
        if not remaining:
            for finding in previous_findings:
                finding.resolved = True
            self.store.findings = previous_findings
        return ResolutionRun(
            status=self.store.status,
            outcome=(
                "Report verified after fresh readback: zero unsupported material claims remain."
                if not remaining
                else f"Report remains blocked with {len(remaining)} findings."
            ),
            resolved_findings=previous - len(remaining),
            remaining_findings=len(remaining),
            events=self.store.events[start:],
        )
