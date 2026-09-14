# AWS deployment

Proofline uses two AWS surfaces with different responsibilities:

- **Amazon Bedrock AgentCore Runtime** hosts the isolated Strands audit loop and emits managed
  logs/traces.
- **AWS App Runner** hosts the public judge console and the human authorization boundary.

The application also supports a direct Bedrock mode for isolating failures during deployment.

## 1. Deploy and prove the AgentCore runtime

Requirements: Node.js 20+, AWS CDK, AgentCore CLI, and an authenticated AWS CLI profile.

```bash
export PATH="/opt/homebrew/opt/node/bin:$PATH"
export AWS_PROFILE=your-profile
export AWS_REGION=us-west-1

agentcore validate -d .
agentcore package -d . -r ProoflineAgent
agentcore deploy -y
agentcore status
agentcore invoke --runtime ProoflineAgent \
  "Audit CYA-2026-017 and stop at the first authorized human decision."
```

Record the runtime ARN reported by `agentcore status`.

## 2. Deploy the public console

The script discovers the current account ID, creates or updates an ECR repository, uses two
least-purpose IAM roles, and creates or updates one App Runner service. No account identifier or
credential is stored in the repository.

To make App Runner use the AgentCore runtime:

```bash
export AWS_PROFILE=your-profile
export AWS_REGION=us-west-2
export AGENTCORE_REGION=us-west-1
export PROOFLINE_AGENT_MODE=agentcore
export AGENTCORE_RUNTIME_ARN=arn:aws:bedrock-agentcore:REGION:ACCOUNT:runtime/NAME
./deployment/deploy-apprunner.sh
```

For direct Strands + Bedrock operation while diagnosing AgentCore, omit the runtime ARN and set
`PROOFLINE_AGENT_MODE=strands`.

## Created resources

- ECR repository `proofline` with scan-on-push enabled.
- IAM access role `ProoflineAppRunnerECRAccess` using the AWS-managed ECR access policy.
- IAM instance role `ProoflineAppRunnerInstance` limited to Nova invocation and the account's
  AgentCore runtimes.
- App Runner service `proofline`, publicly accessible on its generated HTTPS domain.
- AgentCore/CDK resources defined by `agentcore/agentcore.json`.

Keep the App Runner and AgentCore runtime available until the hackathon judging period ends.
