# Agents for Humans: Building an evidence-first Strands agent on AWS

Proofline is a grant-report integrity agent for small nonprofits. It reconciles award obligations,
receipts, invoices, and program logs; catches unsupported claims; and asks for one human decision
before releasing a review packet.

The important architectural question was not simply which model to use. It was where model
judgment should end.

## A Strands loop with five narrow tools

The live path constructs a real `strands.Agent` backed by Amazon Nova on Amazon Bedrock. Its
system prompt gives the agent a workflow objective and an authority boundary. Five tools expose
only the operations it needs:

1. inspect award terms;
2. inspect the evidence inbox;
3. run deterministic integrity checks;
4. prepare one human decision; and
5. verify whether a report packet may be rendered.

This is genuinely agentic work. The model decides which source to inspect next, interprets the
award in context, sequences the investigation, and decides whether the result should remain quiet
or surface a correction. It is not a fixed chatbot prompt wrapped around a form.

The tool set is also intentionally incomplete. There is no tool that approves a correction and no
tool that submits a report to a funder.

## Let the model interpret; let code enforce

Our verifier treats the source files as the authority. It computes SHA-256 hashes to detect
identical uploads, compares transaction dates with the reporting period, sums only unique eligible
evidence, and parses de-identified participant IDs from CSV files to calculate outcome support.

The model may explain that a receipt looks duplicated. It cannot override byte equality. It may
recommend moving an invoice to the next quarter. It cannot change the configured date boundary.
And it may summarize a successful audit, but the packet route independently checks the current
typed state before returning anything.

That separation gives us a useful invariant: no packet becomes ready while a material report
claim lacks matching, in-period, non-duplicated evidence.

## One decision, then a clean-room recheck

On the seeded scenario, the verifier finds four issues: a duplicate receipt, an out-of-period
invoice, a total mismatch, and an unsupported participant count. The Strands loop consolidates
them into one exact decision rather than interrupting the reviewer four times.

Approval happens through a separate application endpoint bound to a concrete decision ID. It
applies only the named changes, then reruns verification from source state. Prior findings remain
visible as resolved. A rejected decision changes nothing.

## Deploying the two product surfaces

The judge-facing console is a small FastAPI application packaged as a Linux container. The agent
loop is designed for Amazon Bedrock AgentCore Runtime, which provides a managed runtime, session
isolation, CloudWatch logs, and agent traces. The web service invokes the same bounded audit path;
the repository also includes a deterministic product twin so tests and public demonstrations do
not become dependent on model latency.

We chose this split because the browser experience and the agent execution have different jobs.
The console owns presentation and human authorization. AgentCore owns managed agent execution.
The verifier owns truth conditions.

## Verifying the pitch

Hackathon demos are easy to overstate, so we encoded the pitch as tests and evaluation scenarios.
The suite checks that all four seeded failures are detected, clean evidence verifies, an approved
correction verifies, blocked reports never emit a packet, evidence drift reopens a report, and no
scenario submits externally.

That evaluation will not prove the product is ready for every grant program. It does make the
specific demonstration falsifiable.

*Proofline is an MIT-licensed Agents for Humans Hackathon project built with Strands Agents SDK,
Amazon Bedrock, and Amazon Bedrock AgentCore.*
