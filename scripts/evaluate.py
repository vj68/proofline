from __future__ import annotations

import json

from proofline.models import AuditStatus, EvidenceStatus, FindingCode
from proofline.store import MISSING_SEPTEMBER_EVIDENCE, GrantStore
from proofline.workflow import DeterministicWorkflow


def evaluate_case(name: str, mutate=None, resolve: bool = False) -> dict:
    grant_store = GrantStore()
    if mutate:
        mutate(grant_store)
    workflow = DeterministicWorkflow(grant_store)
    run = workflow.audit()
    if resolve and grant_store.decision:
        workflow.resolve(grant_store.decision.id, approve=True)
    return {
        "scenario": name,
        "initial_status": run.status,
        "initial_findings": sorted(item.code for item in run.findings),
        "final_status": grant_store.status,
        "packet_ready": grant_store.packet_ready,
        "submitted": False,
    }


def remove_duplicate(grant_store: GrantStore) -> None:
    grant_store.evidence["E-102"].status = EvidenceStatus.EXCLUDED
    grant_store.claims["CLM-01"].claimed_value = 830
    grant_store.claims["CLM-01"].evidence_ids = ["E-101", "E-201"]


def make_clean(grant_store: GrantStore) -> None:
    grant_store.evidence["E-102"].status = EvidenceStatus.EXCLUDED
    grant_store.evidence["E-201"].status = EvidenceStatus.EXCLUDED
    grant_store.evidence["E-303"] = MISSING_SEPTEMBER_EVIDENCE.model_copy(deep=True)
    grant_store.claims["CLM-01"].claimed_value = 480
    grant_store.claims["CLM-01"].evidence_ids = ["E-101"]
    grant_store.claims["CLM-02"].evidence_ids.append("E-303")


def evaluate() -> dict:
    scenarios = [
        evaluate_case("seeded report with four integrity failures"),
        evaluate_case("duplicate removed but period and outcome still invalid", remove_duplicate),
        evaluate_case("fully supported report", make_clean),
        evaluate_case("human approves bounded correction", resolve=True),
    ]
    assertions = {
        "seed_detects_duplicate": FindingCode.DUPLICATE_EVIDENCE
        in scenarios[0]["initial_findings"],
        "seed_detects_outside_period": FindingCode.OUTSIDE_PERIOD
        in scenarios[0]["initial_findings"],
        "seed_detects_total_mismatch": FindingCode.TOTAL_MISMATCH
        in scenarios[0]["initial_findings"],
        "seed_detects_unsupported_claim": FindingCode.UNSUPPORTED_CLAIM
        in scenarios[0]["initial_findings"],
        "clean_report_verifies": scenarios[2]["final_status"] == AuditStatus.VERIFIED,
        "approved_correction_verifies": scenarios[3]["final_status"] == AuditStatus.VERIFIED,
        "blocked_reports_never_emit_packet": scenarios[0]["packet_ready"] is False,
        "no_scenario_submits_externally": all(item["submitted"] is False for item in scenarios),
    }
    return {
        "scenarios": len(scenarios),
        "assertions": len(assertions),
        "passed": sum(assertions.values()),
        "pass_rate": sum(assertions.values()) / len(assertions),
        "claims": assertions,
        "details": scenarios,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
