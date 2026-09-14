# Proofline architecture and trust boundaries

## Product invariant

> Proofline must not mark a grant-report packet ready while any material claim lacks matching,
> in-period, non-duplicated evidence under the configured award policy.

The model can interpret and propose. It cannot grant readiness, approve a correction, change a
source file, or submit a report.

## Runtime flow

```mermaid
sequenceDiagram
    participant E as Evidence event
    participant A as FastAPI
    participant S as Strands agent
    participant B as Amazon Bedrock
    participant T as Audit tools
    participant V as Integrity verifier
    participant H as Human reviewer

    E->>A: evidence-ready event
    A->>S: audit award CYA-2026-017
    S<<->>B: reason about next bounded tool
    S->>T: inspect award and inbox
    T->>V: hashes, dates, totals, ID sets
    V-->>S: BLOCKED + four typed findings
    S-->>H: one bounded correction decision
    H->>A: approve DEC-001
    A->>V: apply exact correction set
    V->>V: fresh scan from current state
    V-->>A: VERIFIED + zero blockers
    A-->>H: review-ready evidence packet
```

## Components

| Component | Responsibility | Cannot do |
|---|---|---|
| Web console | Explain evidence, findings, decision, and before/after state | Grant authority to the model |
| FastAPI | Typed HTTP workflow and state-transition boundary | Emit a blocked packet |
| Strands agent | Interpret obligations, select tools, sequence investigation, produce a concise brief | Approve corrections or submit externally |
| Amazon Bedrock | Model inference for the live loop | Override tool results |
| Audit tools | Narrow, observable access to award, evidence, and verifier operations | Perform arbitrary filesystem or network actions |
| Integrity verifier | Hash de-duplication, period checks, arithmetic, unique-ID coverage, readiness | Interpret ambiguous policy without an encoded rule |
| Human decision endpoint | Bind approval or rejection to a concrete decision ID | Create open-ended authority |
| Packet renderer | Produce a cited review artifact after `verified` state | Render while blockers exist |

## Failure behavior

- Duplicate upload: both artifacts stay visible; one must be explicitly excluded.
- Outside-period invoice: retained for future reporting, excluded from this claim.
- Unsupported outcome: the report stays blocked until supporting IDs arrive or the claim changes.
- Rejected correction: no evidence or claim mutation occurs.
- Evidence drift: a new scan recomputes support and reopens the report when counts diverge.
- Model error or prompt injection: deterministic readiness checks still fail closed.
- AWS unavailable: the deterministic twin demonstrates the same state machine without claiming a
  live model invocation.

## AWS path

The deployed demonstration uses a small, reviewable AWS footprint:

- AWS App Runner in `us-west-2` hosts the public, session-isolated judge console.
- Amazon ECR in `us-west-2` stores the scan-on-push application image.
- Amazon Bedrock AgentCore in `us-west-1` hosts the managed Strands runtime.
- Amazon Bedrock provides Nova Lite through the US cross-region inference profile.

A production rollout can add event-driven intake and durable state without widening the model's
authority:

- Amazon S3 is the production evidence-arrival boundary.
- Amazon EventBridge can schedule deadline checks or react to normalized intake events.
- Amazon DynamoDB can persist report state and idempotency keys.

Only services actually deployed and evidenced should be claimed in the final submission.
