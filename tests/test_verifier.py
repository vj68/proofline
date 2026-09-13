from decimal import Decimal

from proofline.agentcore_client import _hydrate_store
from proofline.models import AuditStatus, EvidenceStatus, FindingCode
from proofline.store import GrantStore
from proofline.verifier import IntegrityVerifier
from proofline.workflow import DeterministicWorkflow


def test_seed_scenario_finds_four_material_blockers() -> None:
    grant_store = GrantStore()
    findings = IntegrityVerifier(grant_store).scan()
    assert {item.code for item in findings} == {
        FindingCode.DUPLICATE_EVIDENCE,
        FindingCode.OUTSIDE_PERIOD,
        FindingCode.TOTAL_MISMATCH,
        FindingCode.UNSUPPORTED_CLAIM,
    }
    total_finding = next(item for item in findings if item.code == FindingCode.TOTAL_MISMATCH)
    assert total_finding.expected == "$480.00"


def test_approved_correction_requires_fresh_verification() -> None:
    grant_store = GrantStore()
    workflow = DeterministicWorkflow(grant_store)
    first = workflow.audit()
    assert first.status == AuditStatus.BLOCKED
    assert grant_store.packet_ready is False
    assert grant_store.decision is not None

    result = workflow.resolve(grant_store.decision.id, approve=True)
    assert result.status == AuditStatus.VERIFIED
    assert result.remaining_findings == 0
    assert grant_store.packet_ready is True
    assert grant_store.evidence["E-102"].status == EvidenceStatus.EXCLUDED
    assert grant_store.evidence["E-201"].status == EvidenceStatus.EXCLUDED
    assert "E-303" in grant_store.evidence


def test_rejection_never_mutates_evidence() -> None:
    grant_store = GrantStore()
    workflow = DeterministicWorkflow(grant_store)
    workflow.audit()
    before_hashes = {item.id: item.sha256 for item in grant_store.evidence.values()}

    result = workflow.resolve("DEC-001", approve=False)
    assert result.status == AuditStatus.BLOCKED
    assert result.resolved_findings == 0
    assert before_hashes == {item.id: item.sha256 for item in grant_store.evidence.values()}
    assert all(item.status == EvidenceStatus.INCLUDED for item in grant_store.evidence.values())


def test_verified_financial_total_is_recomputed_from_included_evidence() -> None:
    grant_store = GrantStore()
    workflow = DeterministicWorkflow(grant_store)
    workflow.audit()
    workflow.resolve("DEC-001", approve=True)

    included_total = sum(
        Decimal(str(item.amount or 0))
        for item in grant_store.evidence.values()
        if item.status == EvidenceStatus.INCLUDED
        and grant_store.award.reporting_start <= item.captured_on <= grant_store.award.reporting_end
    )
    assert included_total == Decimal("480.0")
    assert Decimal(str(grant_store.claims["CLM-01"].claimed_value)) == included_total


def test_evidence_drift_reopens_verified_report() -> None:
    grant_store = GrantStore()
    workflow = DeterministicWorkflow(grant_store)
    workflow.audit()
    workflow.resolve("DEC-001", approve=True)
    grant_store.evidence["E-303"].participant_ids = grant_store.evidence["E-303"].participant_ids[:30]

    findings = IntegrityVerifier(grant_store).scan()
    assert len(findings) == 1
    assert findings[0].code == FindingCode.UNSUPPORTED_CLAIM


def test_agentcore_result_hydrates_console_state() -> None:
    remote_store = GrantStore()
    remote_run = DeterministicWorkflow(remote_store).audit()
    local_store = GrantStore()

    run = _hydrate_store(
        local_store,
        {
            "audit": remote_run.model_dump(mode="json"),
            "decision": remote_store.decision.model_dump(mode="json"),
            "packet_ready": False,
        },
    )

    assert run.agent_mode == "agentcore"
    assert local_store.agent_mode == "agentcore"
    assert local_store.status == AuditStatus.BLOCKED
    assert local_store.decision is not None
    assert len(local_store.findings) == 4
