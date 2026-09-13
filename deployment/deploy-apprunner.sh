#!/usr/bin/env bash
set -euo pipefail

: "${AWS_PROFILE:?Set AWS_PROFILE to the profile that owns the deployment.}"

deployment_region="${AWS_REGION:-us-west-2}"
service_name="proofline"
repository_name="proofline"
access_role_name="ProoflineAppRunnerECRAccess"
instance_role_name="ProoflineAppRunnerInstance"
deployment_mode="${PROOFLINE_AGENT_MODE:-strands}"

account_id="$(aws sts get-caller-identity --profile "$AWS_PROFILE" --query Account --output text)"
image_uri="${account_id}.dkr.ecr.${deployment_region}.amazonaws.com/${repository_name}:latest"

if ! aws ecr describe-repositories \
  --profile "$AWS_PROFILE" \
  --region "$deployment_region" \
  --repository-names "$repository_name" >/dev/null 2>&1; then
  aws ecr create-repository \
    --profile "$AWS_PROFILE" \
    --region "$deployment_region" \
    --repository-name "$repository_name" \
    --image-scanning-configuration scanOnPush=true >/dev/null
fi

aws ecr get-login-password --profile "$AWS_PROFILE" --region "$deployment_region" |
  docker --context colima login \
    --username AWS \
    --password-stdin "${account_id}.dkr.ecr.${deployment_region}.amazonaws.com"

docker --context colima build --platform linux/amd64 -t "${repository_name}:latest" .
docker --context colima tag "${repository_name}:latest" "$image_uri"
docker --context colima push "$image_uri"

access_trust="$(jq -cn '{Version:"2012-10-17",Statement:[{Effect:"Allow",Principal:{Service:"build.apprunner.amazonaws.com"},Action:"sts:AssumeRole"}]}')"
if ! aws iam get-role --profile "$AWS_PROFILE" --role-name "$access_role_name" >/dev/null 2>&1; then
  aws iam create-role \
    --profile "$AWS_PROFILE" \
    --role-name "$access_role_name" \
    --assume-role-policy-document "$access_trust" >/dev/null
fi
aws iam attach-role-policy \
  --profile "$AWS_PROFILE" \
  --role-name "$access_role_name" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess

instance_trust="$(jq -cn '{Version:"2012-10-17",Statement:[{Effect:"Allow",Principal:{Service:"tasks.apprunner.amazonaws.com"},Action:"sts:AssumeRole"}]}')"
if ! aws iam get-role --profile "$AWS_PROFILE" --role-name "$instance_role_name" >/dev/null 2>&1; then
  aws iam create-role \
    --profile "$AWS_PROFILE" \
    --role-name "$instance_role_name" \
    --assume-role-policy-document "$instance_trust" >/dev/null
fi

runtime_resource="arn:aws:bedrock-agentcore:${deployment_region}:${account_id}:runtime/*"
instance_policy="$(jq -cn \
  --arg model "arn:aws:bedrock:${deployment_region}::foundation-model/amazon.nova-lite-v1:0" \
  --arg profile "arn:aws:bedrock:${deployment_region}:${account_id}:inference-profile/*" \
  --arg runtime "$runtime_resource" \
  '{Version:"2012-10-17",Statement:[
    {Sid:"InvokeNova",Effect:"Allow",Action:["bedrock:InvokeModel","bedrock:InvokeModelWithResponseStream"],Resource:[$model,$profile]},
    {Sid:"InvokeProoflineAgentCore",Effect:"Allow",Action:["bedrock-agentcore:InvokeAgentRuntime"],Resource:[$runtime]}
  ]}')"
aws iam put-role-policy \
  --profile "$AWS_PROFILE" \
  --role-name "$instance_role_name" \
  --policy-name ProoflineRuntimeAccess \
  --policy-document "$instance_policy"

access_role_arn="arn:aws:iam::${account_id}:role/${access_role_name}"
instance_role_arn="arn:aws:iam::${account_id}:role/${instance_role_name}"

runtime_variables="$(jq -cn \
  --arg mode "$deployment_mode" \
  --arg region "$deployment_region" \
  --arg model "amazon.nova-lite-v1:0" \
  '[
    {Name:"PROOFLINE_AGENT_MODE",Value:$mode},
    {Name:"AWS_REGION",Value:$region},
    {Name:"BEDROCK_MODEL_ID",Value:$model}
  ]')"
if [[ "$deployment_mode" == "agentcore" ]]; then
  : "${AGENTCORE_RUNTIME_ARN:?Set AGENTCORE_RUNTIME_ARN when deploying in agentcore mode.}"
  runtime_variables="$(jq -cn \
    --arg mode "$deployment_mode" \
    --arg region "$deployment_region" \
    --arg model "amazon.nova-lite-v1:0" \
    --arg arn "$AGENTCORE_RUNTIME_ARN" \
    '[
      {Name:"PROOFLINE_AGENT_MODE",Value:$mode},
      {Name:"AWS_REGION",Value:$region},
      {Name:"BEDROCK_MODEL_ID",Value:$model},
      {Name:"AGENTCORE_RUNTIME_ARN",Value:$arn}
    ]')"
fi

source_configuration="$(jq -cn \
  --arg image "$image_uri" \
  --arg access "$access_role_arn" \
  --argjson variables "$runtime_variables" \
  '{
    AuthenticationConfiguration:{AccessRoleArn:$access},
    AutoDeploymentsEnabled:false,
    ImageRepository:{
      ImageIdentifier:$image,
      ImageConfiguration:{Port:"8080",RuntimeEnvironmentVariables:$variables},
      ImageRepositoryType:"ECR"
    }
  }')"

service_arn="$(aws apprunner list-services \
  --profile "$AWS_PROFILE" \
  --region "$deployment_region" \
  --query "ServiceSummaryList[?ServiceName=='${service_name}'].ServiceArn | [0]" \
  --output text)"

if [[ "$service_arn" == "None" ]]; then
  service_arn="$(aws apprunner create-service \
    --profile "$AWS_PROFILE" \
    --region "$deployment_region" \
    --service-name "$service_name" \
    --source-configuration "$source_configuration" \
    --instance-configuration "Cpu=1 vCPU,Memory=2 GB,InstanceRoleArn=${instance_role_arn}" \
    --health-check-configuration 'Protocol=HTTP,Path=/api/health,Interval=10,Timeout=5,HealthyThreshold=1,UnhealthyThreshold=5' \
    --tags Key=project,Value=proofline Key=hackathon,Value=agents-for-humans \
    --query Service.ServiceArn \
    --output text)"
else
  aws apprunner update-service \
    --profile "$AWS_PROFILE" \
    --region "$deployment_region" \
    --service-arn "$service_arn" \
    --source-configuration "$source_configuration" \
    --instance-configuration "Cpu=1 vCPU,Memory=2 GB,InstanceRoleArn=${instance_role_arn}" >/dev/null
fi

for attempt in {1..60}; do
  service_status="$(aws apprunner describe-service \
    --profile "$AWS_PROFILE" \
    --region "$deployment_region" \
    --service-arn "$service_arn" \
    --query Service.Status \
    --output text)"
  if [[ "$service_status" == "RUNNING" ]]; then
    break
  fi
  if [[ "$service_status" == "CREATE_FAILED" || "$service_status" == "DELETE_FAILED" ]]; then
    printf 'App Runner entered terminal status: %s\n' "$service_status" >&2
    exit 1
  fi
  if [[ "$attempt" == "60" ]]; then
    printf 'Timed out waiting for App Runner; last status: %s\n' "$service_status" >&2
    exit 1
  fi
  sleep 10
done

service_url="$(aws apprunner describe-service \
  --profile "$AWS_PROFILE" \
  --region "$deployment_region" \
  --service-arn "$service_arn" \
  --query Service.ServiceUrl \
  --output text)"

printf 'Proofline is live: https://%s\n' "$service_url"
