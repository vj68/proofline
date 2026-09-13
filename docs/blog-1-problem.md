# Agents for Humans: Why grant reporting is an evidence problem, not a writing problem

Small nonprofits are often told that AI can help them write grants. That matters, but it misses a
less visible burden: after an award arrives, the organization must repeatedly prove how money was
spent and what the program accomplished.

That proof rarely lives in one place. The award document defines reporting periods and required
fields. Receipts arrive through email or shared drives. Financial exports use accounting codes.
Program staff maintain attendance or delivery logs. A narrative report then compresses all of
that into a few confident sentences and totals.

The recurring task is not “write something persuasive.” It is “make sure every material claim can
be defended by the current evidence.”

## The failure that shaped our demo

We designed Proofline around a narrow quarterly-report scenario. A fictional youth organization
has a draft claiming 1,310 dollars of eligible spending and 92 unique participants. Its evidence
inbox contains:

- two files containing the same 480-dollar receipt;
- one 350-dollar invoice dated just after the reporting period;
- July and August attendance logs supporting only 59 unique participant IDs; and
- a September log that exists but has not been attached to the report.

Each failure looks small. Together, they can create a report that is fluent, plausible, and wrong.
They also reflect a real class of work. The U.S. Government Accountability Office has described
how grant-management requirements consume recipient capacity, and Grants.gov frames post-award
implementation, reporting, and closeout as a continuing workload with award-specific schedules.

## What a useful background agent should do

The Agents for Humans brief asks for agents that handle repetitive tasks in the background and
surface only when there is a real decision. That led us to three product rules.

First, the agent should investigate the full report, not turn every inconsistency into a separate
notification. Second, it should convert related failures into one bounded correction decision.
Third, it must not confuse a plausible model response with evidence.

Proofline therefore performs an autonomous audit, then asks the reviewer one question: should it
exclude but retain the duplicate, carry the October invoice forward, attach the available
September log, and recalculate the draft? After approval, it starts a fresh scan from source state.
Only a report with zero unsupported material claims can produce a packet.

## Why we chose synthetic source files

Grant evidence can contain names, financial details, addresses, and sensitive information about
program participants. Public demonstrations do not need that risk. Our repository includes a
fictional award, text receipts, and de-identified attendance CSVs. The files themselves are real
fixtures: their hashes, dates, amounts, and unique ID counts are computed at runtime. The facts are
synthetic; the workflow and failure modes are not.

This also makes the demonstration reproducible. A judge or developer can run the same audit,
inspect the exact inputs, and verify the expected findings without access to a nonprofit's private
records.

## A deliberately narrow promise

Proofline does not certify regulatory compliance, detect all fraud, decide whether an ambiguous
cost is legally allowable, or file reports with funders. It prepares a traceable packet for an
authorized person. That narrow promise is central to its usefulness: community organizations get
less reconciliation work without silently giving a language model financial authority.

Most grant AI helps people create more text. We built Proofline to help them trust the claims they
already need to make.

*Proofline is an open-source entry for the Agents for Humans Hackathon. The public demo uses only
synthetic organization, award, receipt, and participant data.*

**Read further:** [Proofline source code](https://github.com/vj68/proofline) ·
[GAO nonprofit grant study](https://www.gao.gov/products/gao-10-477) ·
[GAO grant-management observations](https://www.gao.gov/products/gao-23-106797) ·
[Grants.gov post-award guidance](https://www.grants.gov/learn-grants/grants-101/post-award-phase)
