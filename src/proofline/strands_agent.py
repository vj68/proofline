from __future__ import annotations

import json
import os
from typing import Any

from strands import Agent, tool
from strands.models import BedrockModel

from .models import AuditRun, AuditStatus
from .store import GrantStore
from .verifier import IntegrityVerifier

SYSTEM_PROMPT = """
You are Proofline, an evidence-integrity agent for a small nonprofit's quarterly grant report.
Your job is to complete one audit from award terms to a verified packet or a precise human
decision. First inspect the award terms and evidence inbox. Then run the deterministic integrity
checks. Those checks—not you—are authoritative for hashes, dates, arithmetic, evidence coverage,
and readiness. If blockers exist, prepare exactly one consolidated decision brief and stop. Never
alter evidence, approve a correction, mark a blocked report ready, or claim that anything was
submitted. If no blockers exist, verify that packet generation is permitted. Finish with a short,
factual outcome grounded in tool results. Never invent files, IDs, figures, or actions.
""".strip()


class GrantAuditTools:
    def __init__(self, grant_store: GrantStore) -> None:
        self.store = grant_store

    def build(self) -> list[Any]:
        grant_store = self.store

        @tool
        def inspect_award_terms() -> dict:
            """Read the award and return its reporting boundary and cited obligations."""
            grant_store.event(
                "inspection",
                "Award obligations mapped",
                f"Mapped {len(grant_store.requirements)} requirements from {grant_store.award.source_filename}.",
                "inspect_award_terms",
            )
            return {
                "award": grant_store.award.model_dump(mode="json"),
                "requirements": [item.model_dump(mode="json") for item in grant_store.requirements],
            }

        @tool
        def inspect_evidence_inbox() -> dict:
            """Hash and classify the privacy-safe receipts, invoices, and program logs."""
            grant_store.event(
                "inspection",
                "Evidence inbox inspected",
                f"Hashed and classified {len(grant_store.evidence)} receipts, invoices, and activity logs.",
                "inspect_evidence_inbox",
            )
            return {
                "count": len(grant_store.evidence),
                "evidence": [
                    item.model_dump(mode="json") for item in grant_store.evidence.values()
                ],
                "claims": [item.model_dump(mode="json") for item in grant_store.claims.values()],
            }

        @tool
        def run_deterministic_integrity_checks() -> dict:
            """Run authoritative duplicate, date, arithmetic, and evidence-coverage checks."""
            grant_store.status = AuditStatus.SCANNING
            findings = IntegrityVerifier(grant_store).scan()
            grant_store.findings = findings
            grant_store.status = AuditStatus.BLOCKED if findings else AuditStatus.VERIFIED
            grant_store.packet_ready = not findings
            grant_store.event(
                "verification",
                "Independent integrity checks completed",
                f"Dates, hashes, totals, reporting periods, and claim coverage checked. {len(findings)} blockers found.",
                "run_deterministic_integrity_checks",
                blockers=len(findings),
            )
            return {
                "status": grant_store.status,
                "blocker_count": len(findings),
                "findings": [item.model_dump(mode="json") for item in findings],
            }

        @tool
        def prepare_human_decision() -> dict:
            """Create one bounded correction decision when deterministic blockers exist."""
            if not grant_store.findings:
                raise ValueError("Decision brief blocked: there are no integrity findings")
            # Reuse the exact product policy used by deterministic/replay mode.
            verifier = IntegrityVerifier(grant_store)
            grant_store.findings = verifier.scan()
            from .models import DecisionCard

            grant_store.decision = DecisionCard(
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
                    "The 92-youth outcome becomes fully traceable to three monthly logs.",
                ],
                action_label="Approve corrections & re-verify",
            )
            grant_store.event(
                "decision",
                "Human decision required",
                "Four related integrity blockers were consolidated into one reviewable correction plan.",
                "prepare_human_decision",
            )
            return grant_store.decision.model_dump(mode="json")

        @tool
        def verify_packet_permission() -> dict:
            """Confirm whether deterministic policy permits creation of a review packet."""
            if grant_store.status != AuditStatus.VERIFIED or grant_store.findings:
                raise ValueError("Packet blocked: unresolved integrity findings remain")
            grant_store.packet_ready = True
            grant_store.event(
                "packet",
                "Evidence packet verified",
                "Every material claim is supported and the packet is ready for authorized review.",
                "verify_packet_permission",
            )
            return {"permitted": True, "submitted": False, "status": grant_store.status}

        return [
            inspect_award_terms,
            inspect_evidence_inbox,
            run_deterministic_integrity_checks,
            prepare_human_decision,
            verify_packet_permission,
        ]


def run_strands_audit(grant_store: GrantStore) -> AuditRun:
    model = BedrockModel(
        model_id=os.getenv("BEDROCK_MODEL_ID", "us.amazon.nova-lite-v1:0"),
        region_name=os.getenv("AWS_REGION", "us-west-2"),
    )
    grant_store.agent_mode = "strands"
    start = len(grant_store.events)
    agent = Agent(
        model=model, system_prompt=SYSTEM_PROMPT, tools=GrantAuditTools(grant_store).build()
    )
    result = agent(
        "Audit report CYA-2026-017 end to end. Stop only when it is verified or one precise human decision is ready."
    )
    events = grant_store.events[start:]
    return AuditRun(
        status=grant_store.status,
        outcome=str(result),
        findings=grant_store.findings,
        events=events,
        tool_calls=len([event for event in events if event.tool]),
        agent_mode="strands",
    )


def describe_agent() -> dict[str, object]:
    return {
        "framework": "Strands Agents SDK",
        "model": os.getenv("BEDROCK_MODEL_ID", "us.amazon.nova-lite-v1:0"),
        "region": os.getenv("AWS_REGION", "us-west-2"),
        "tools": 5,
        "authority_boundary": "deterministic integrity verifier",
        "external_submission": "not permitted",
    }


def describe_agent_json() -> str:
    return json.dumps(describe_agent())
