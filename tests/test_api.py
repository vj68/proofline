from fastapi.testclient import TestClient

from proofline.main import app

client = TestClient(app)


def test_complete_golden_path() -> None:
    client.post("/api/reset")
    initial = client.get("/api/state")
    assert initial.status_code == 200
    assert initial.json()["status"] == "ready"

    audit = client.post("/api/audits/CYA-2026-017/run")
    assert audit.status_code == 200
    assert audit.json()["status"] == "blocked"
    assert len(audit.json()["findings"]) == 4

    premature_packet = client.get("/api/reports/CYA-2026-017/packet")
    assert premature_packet.status_code == 409

    resolution = client.post(
        "/api/audits/CYA-2026-017/resolve",
        json={"decision_id": "DEC-001", "approve": True},
    )
    assert resolution.status_code == 200
    assert resolution.json()["status"] == "verified"

    packet = client.get("/api/reports/CYA-2026-017/packet")
    assert packet.status_code == 200
    assert "0 unsupported material claims" in packet.text
    assert "has not been submitted externally" in packet.text


def test_unknown_award_is_404() -> None:
    assert client.post("/api/audits/missing/run").status_code == 404


def test_duplicate_audit_is_rejected() -> None:
    client.post("/api/reset")
    client.post("/api/audits/CYA-2026-017/run")
    assert client.post("/api/audits/CYA-2026-017/run").status_code == 409


def test_health_discloses_authority_boundary() -> None:
    health = client.get("/api/health").json()
    assert health["status"] == "ok"
    assert health["agent"]["framework"] == "Strands Agents SDK"
    assert health["agent"]["external_submission"] == "not permitted"


def test_public_browser_sessions_are_isolated() -> None:
    session_a = {"X-Proofline-Session": "judge-a"}
    session_b = {"X-Proofline-Session": "judge-b"}
    client.post("/api/reset", headers=session_a)
    client.post("/api/reset", headers=session_b)

    assert client.post("/api/audits/CYA-2026-017/run", headers=session_a).status_code == 200
    assert client.get("/api/state", headers=session_a).json()["status"] == "blocked"
    assert client.get("/api/state", headers=session_b).json()["status"] == "ready"
