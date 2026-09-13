# Agents for Humans: Human-in-the-loop is a product boundary, not a disclaimer

“A human should review this” is common language in AI products. It is also often too vague to be
useful. If the system hands someone an entire report and asks them to check everything, the human
still owns all the repetitive work. If the system silently takes action and adds a disclaimer, the
human does not meaningfully control the outcome.

While building Proofline, our grant-report integrity agent, we tried to make human authority a
visible state transition.

## A decision should be bounded

Proofline investigates a report in the background. In our demonstration it discovers four related
problems across financial and attendance evidence. It does not send four notifications. It
prepares one correction card that names the exact proposed actions and their consequences:

- exclude one byte-identical duplicate while preserving it in the evidence trail;
- retain an October invoice for the next reporting period;
- attach a named September attendance file; and
- recalculate the reported expense total from eligible unique records.

The reviewer can approve or reject that specific correction. They are not granting open-ended
permission to “fix the report.”

## Authority should be absent from the agent's tools

Prompt instructions alone are not a strong authorization boundary. Proofline's Strands agent
simply does not receive an approval tool or an external-submission tool. The approval endpoint is
separate, expects the current decision identifier, and only applies the predefined correction set.

This reduces the consequence of prompt injection or model error. A model could produce a poor
summary, but it still cannot approve itself. It could call the packet-permission tool too early,
but the deterministic verifier would return a blocked state.

## Verification should start again after a correction

A common workflow bug is to mark individual alerts “resolved” and assume the whole object is now
valid. Proofline instead reruns all integrity checks after the human decision. If attached evidence
changes the participant count, the total is recomputed. If evidence later drifts, a new audit can
reopen the report.

The prior findings do not disappear. They remain in the interface as resolved history, alongside
the tool trail and the current evidence disposition. This gives a reviewer both the clean present
state and the reason it changed.

## Safety must be honest about scope

Proofline's `verified` status has a precise meaning: the demonstrated material claims reconcile to
the supplied evidence under the configured policy. It does not prove the absence of fraud, replace
an accountant, determine every question of cost allowability, or certify legal compliance.

That limitation is not tucked into terms of service. The product shows “review-ready, never
auto-submitted” next to the status. The packet is a cited preparation artifact for an authorized
person.

## The practical lesson

Human-in-the-loop works best when three things are clear:

1. what the agent completed autonomously;
2. the exact decision only a person can make; and
3. the independent condition that must pass afterward.

For Proofline, those are investigation, a bounded correction, and evidence-backed verification.
That shape lets an agent remove busywork without removing responsibility.

*This post covers the design of Proofline, an open-source Agents for Humans Hackathon entry. Its
public demonstration uses synthetic financial and participant data.*

**Inspect the safeguards:** [Proofline source code](https://github.com/vj68/proofline) ·
[architecture and trust boundaries](https://github.com/vj68/proofline/blob/main/docs/architecture.md) ·
[evaluation scenarios](https://github.com/vj68/proofline/blob/main/scripts/evaluate.py)
