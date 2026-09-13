# Proofline — Agents for Humans demo

Proofline is a grant-report integrity agent for small nonprofits: every material claim is traced
to evidence before an authorized human can submit it.

In this end-to-end demonstration, a Strands agent running with Amazon Nova on Amazon Bedrock and
Amazon Bedrock AgentCore inspects an award, receipts, invoices, and de-identified attendance
logs. It finds four connected report failures, consolidates them into one bounded correction
decision, and starts a fresh deterministic verification pass after human approval. The model
cannot approve its own correction and has no external-submission tool.

All organization, award, financial, and participant data shown are synthetic. The files are real
repository fixtures whose hashes, dates, totals, and unique IDs are computed at runtime.

- Live demo: **ADD DEPLOYED URL**
- MIT-licensed source: https://github.com/vj68/proofline
- Architecture: https://github.com/vj68/proofline/blob/main/docs/architecture.md
- Agents for Humans Hackathon: https://agentsforhumans.devpost.com/

Built with Strands Agents SDK, Amazon Bedrock, Amazon Nova, FastAPI, and Amazon Bedrock AgentCore.
