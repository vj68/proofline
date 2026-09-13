from __future__ import annotations

from typing import Any

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from proofline.store import GrantStore
from proofline.strands_agent import describe_agent, run_strands_audit

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict[str, Any], context: Any) -> dict[str, Any]:
    """Run a fresh, isolated Proofline audit inside AgentCore Runtime."""
    if not isinstance(payload, dict):
        raise TypeError("payload must be a JSON object")
    prompt = payload.get(
        "prompt",
        "Audit report CYA-2026-017 and stop at the first authorized human decision.",
    )
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must be a non-empty string")

    grant_store = GrantStore()
    audit = run_strands_audit(grant_store)
    return {
        "request": prompt,
        "session_id": getattr(context, "session_id", None),
        "agent": describe_agent(),
        "audit": audit.model_dump(mode="json"),
        "decision": (
            grant_store.decision.model_dump(mode="json") if grant_store.decision else None
        ),
        "packet_ready": grant_store.packet_ready,
        "external_submission": False,
    }


if __name__ == "__main__":
    app.run()
