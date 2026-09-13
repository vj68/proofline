# Proofline demo script — 4:20 target

The recording should be one continuous product story. Keep the cursor deliberate, enlarge browser
text enough for mobile judging, and let the live status changes carry the technical explanation.

## 0:00–0:25 — Hook

**Visual:** Proofline hero and the report due date.

**Voiceover:**

> Small nonprofits do not just have to win grants. They have to prove every dollar and every
> outcome afterward—often with one person reconciling award terms, receipts, and program logs.
> Proofline is a background integrity agent that traces every material report claim before it can
> leave the organization.

## 0:25–0:50 — Person and stakes

**Visual:** Scroll across the award, claimed total, and youth outcome.

**Voiceover:**

> This is a synthetic but realistic quarterly report for a youth nonprofit. It claims 1,310
> dollars of spending and 92 unique youth served. The reviewer should not need to manually compare
> every artifact—and an unsupported report can damage trust, delay reimbursement, or create audit
> work later.

## 0:50–1:55 — Autonomous audit

**Action:** Select **Run evidence audit**. Pause while the activity rail advances.

**Voiceover:**

> A real Strands agent running with Amazon Bedrock decides which bounded tool to call next. It
> reads the award obligations, inventories the evidence, runs the integrity checks, and determines
> whether a packet may be released. The agent is autonomous about investigation, but not about
> truth or authority.

**Visual:** Point to all four finding cards.

> Proofline found four connected blockers. The same 480-dollar receipt was uploaded twice. A
> 350-dollar invoice belongs to the next quarter. The claimed total therefore does not reconcile:
> only 480 dollars is supported. And the attendance files support 59—not 92—unique youth.

## 1:55–2:35 — One human decision

**Visual:** Correction card.

**Voiceover:**

> Four alerts would still leave the busywork with the reviewer. Proofline consolidates them into
> one bounded decision: exclude but retain the duplicate, carry the October invoice forward,
> attach the available September log, and recalculate the draft. The model has no tool that can
> approve this action and no tool that can submit a report.

**Action:** Select **Approve exact correction**.

## 2:35–3:20 — Fresh verification

**Visual:** Verified state, resolved findings, evidence labels, zero blockers.

**Voiceover:**

> Approval changes only the named records. Proofline then starts a fresh deterministic scan from
> source state. Hash equality, reporting dates, arithmetic, and de-identified participant IDs are
> computed in code—not accepted from model prose. All four findings remain visible as resolved,
> while the current report reaches zero unsupported material claims.

**Action:** Open **View verified packet**.

> Only now does the fail-closed packet route return a cited review packet. This is ready for human
> review, not automatically submitted.

## 3:20–3:55 — Architecture and technical proof

**Visual:** Architecture diagram, then briefly the five tool names in GitHub.

**Voiceover:**

> The experience is a FastAPI web app. The reasoning loop uses Strands Agents SDK and Amazon Nova
> on Bedrock, deployed to AgentCore Runtime for managed sessions and traces. Five narrow tools sit
> between the agent and a deterministic integrity verifier. The public repository includes the
> source fixtures, typed contracts, eleven tests, and four-scenario evaluation.

## 3:55–4:20 — Close

**Visual:** Return to verified Proofline screen and tagline.

**Voiceover:**

> Most grant AI helps people write more. Proofline helps community organizations prove what is
> already true. It quietly handles the reconciliation, surfaces only a real decision, and never
> lets fluent text outrank evidence. Proofline: every grant-report claim, traced before submission.

## Recording checklist

- Keep the final upload below five minutes and public on YouTube or Vimeo.
- Show the live URL in the address bar once.
- Capture the runtime badge saying `LIVE AGENTCORE LOOP`.
- Do not expose the AWS account number, console identity, or credentials.
- Use the synthetic-data disclosure on screen or in the video description.
- End on a verified state with the packet link visible.
