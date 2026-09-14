from __future__ import annotations

import json
import os
import uuid
from typing import Any

import boto3

from .models import AuditRun, DecisionCard
from .store import GrantStore


def _hydrate_store(grant_store: GrantStore, payload: dict[str, Any]) -> AuditRun:
    """Apply the typed result of an isolated AgentCore audit to the web session."""
    run = AuditRun.model_validate(payload["audit"])
    grant_store.status = run.status
    grant_store.findings = run.findings
    grant_store.events = run.events
    grant_store.decision = (
        DecisionCard.model_validate(payload["decision"]) if payload.get("decision") else None
    )
    grant_store.packet_ready = bool(payload.get("packet_ready", False))
    grant_store.agent_mode = "agentcore"
    return run.model_copy(update={"agent_mode": "agentcore"})


def run_agentcore_audit(grant_store: GrantStore) -> AuditRun:
    """Invoke the managed AgentCore runtime and mirror its audit result for the console."""
    runtime_arn = os.getenv("AGENTCORE_RUNTIME_ARN")
    if not runtime_arn:
        raise RuntimeError("AGENTCORE_RUNTIME_ARN is required in agentcore mode")

    client = boto3.client(
        "bedrock-agentcore",
        region_name=os.getenv("AGENTCORE_REGION", os.getenv("AWS_REGION", "us-west-2")),
    )
    response = client.invoke_agent_runtime(
        agentRuntimeArn=runtime_arn,
        runtimeSessionId=str(uuid.uuid4()),
        qualifier="DEFAULT",
        contentType="application/json",
        accept="application/json",
        payload=json.dumps(
            {
                "prompt": (
                    "Audit report CYA-2026-017 end to end and stop at the first authorized "
                    "human decision."
                )
            }
        ).encode(),
    )
    raw = response["response"].read()
    result = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
    return _hydrate_store(grant_store, result)
