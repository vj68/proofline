# Devpost submission draft

## Project name

Proofline *(working name; may change before submission)*

## Tagline

Every grant-report claim, traced before submission.

## Track

Good Neighbor Agents

## Inspiration

Small nonprofits win funding to serve people, then lose scarce staff capacity proving what they
did. Grant requirements, receipts, financial exports, attendance logs, and narrative claims live
in different places. GAO has repeatedly documented the burden of post-award grant management, and
a recent nonprofit worker described a quarterly report that included a duplicate receipt and an
expense for an activity that had not happened yet.

Most grant AI helps organizations find or write grants. We focused on the less glamorous moment
after the award: before a report leaves the organization, can every material claim be defended?

## What it does

Proofline is a background grant-report integrity agent. A Strands agent maps award obligations,
inspects a privacy-safe evidence inbox, and invokes deterministic checks for duplicate artifacts,
reporting-period boundaries, arithmetic, and source coverage. When the draft cannot be supported,
it does not produce more prose. It stops and gives the reviewer one exact correction decision.

In the working demo, Proofline catches four related failures: a duplicated USD 480 receipt, a USD
350 invoice from the next period, a USD 1,310 total that cannot be reconciled, and 33 reported
youth without a supporting attendance log. A human approves the bounded correction. Proofline
retains the excluded evidence, attaches the available log, recomputes unique participant IDs,
reruns every check, and releases a cited packet only after reaching zero unsupported claims.

Proofline never submits externally and cannot approve its own correction.

## How we built it

The live reasoning loop uses Strands Agents SDK and Amazon Bedrock. Five narrow tools expose award
inspection, evidence inspection, deterministic verification, decision preparation, and packet
permission. The model controls sequencing and contextual interpretation; typed Python controls
hashes, dates, de-duplication, unique-ID counting, arithmetic, and readiness.

FastAPI serves a responsive evidence console and typed API. The same policy runs in a deterministic
twin for repeatable judge demos and automated evaluation. All fixture hashes are computed from
real repository files at runtime. The packet renderer fails closed unless the current state has
passed a fresh verification.

## What we are proud of

- One coherent end-to-end workflow rather than a feature montage.
- A clear authority boundary: the agent may investigate and propose, but evidence controls status.
- One human decision instead of four noisy alerts.
- Visible provenance and an append-only tool trail.
- Honest synthetic data with no exposed nonprofit or participant information.
- Reproducible tests and evaluations for the exact claims in the pitch.

## What we learned

Grant reporting is not primarily a writing problem. It is an evidence-reconciliation problem.
Making the model more fluent does not prevent an unsupported report; giving deterministic policy
the final word does.

We also learned that human-in-the-loop is useful only when the decision is bounded. “Review this
report” is work. “Exclude this duplicate, carry this invoice forward, and attach this named log”
is a decision.

## What's next

- Organization-specific grant-policy templates reviewed with real grant managers.
- S3 evidence intake, EventBridge scheduling, and durable DynamoDB state.
- Accounting-system and grants-portal connectors with separate least-authority scopes.
- Multi-grant deadline monitoring and reimbursement-packet support.
- User research with nonprofit finance, program, and development teams.

## Data disclosure

The organization, award, receipts, and participant IDs in the public demo are synthetic. Public
GAO and Grants.gov material supports the problem statement and workflow design. No real PII,
financial records, or confidential grant documents are used.
