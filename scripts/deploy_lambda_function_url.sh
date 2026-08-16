#!/usr/bin/env bash
set -euo pipefail

FUNCTION_NAME="${ORPHANPROOF_LAMBDA_FUNCTION_NAME:-cloud-nexus-orphanproof-demo}"
ROLE_NAME="${ORPHANPROOF_LAMBDA_ROLE_NAME:-cloud-nexus-orphanproof-lambda-role}"
REGION="${ORPHANPROOF_AWS_REGION:-us-east-1}"
PARAMETER_NAME="${ORPHANPROOF_DATABASE_URL_PARAMETER_NAME:-/orphanproof/prod/database-url}"
BUILD_DIR="build/lambda"
PACKAGE_PATH="build/orphanproof-lambda.zip"
PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
COCKROACH_CA_CERT_SOURCE="${ORPHANPROOF_COCKROACH_CA_CERT_SOURCE:-$HOME/.postgresql/root.crt}"
LAMBDA_COCKROACH_CA_CERT_PATH="/var/task/cockroach-ca.crt"

if [[ -z "${DATABASE_URL:-}" ]]; then
  if [[ -f ".env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source ".env"
    set +a
  fi
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL_PRESENT=False"
  echo "STOP: Set DATABASE_URL in the local ignored .env or environment before deployment."
  exit 1
fi

echo "DATABASE_URL_PRESENT=True"
echo "AWS_CLI_AVAILABLE=True"
aws configure list >/dev/null
echo "AWS_CREDENTIAL_PROVIDER_AVAILABLE=True"

mkdir -p build
SECRET_INPUT="$(mktemp)"
TRUST_POLICY="$(mktemp)"
ROLE_POLICY="$(mktemp)"
trap 'rm -f "$SECRET_INPUT" "$TRUST_POLICY" "$ROLE_POLICY"' EXIT
chmod 600 "$SECRET_INPUT" "$TRUST_POLICY" "$ROLE_POLICY"

export PARAMETER_NAME DATABASE_URL
"$PYTHON_BIN" -c 'import json, os, sys; json.dump({"Name": os.environ["PARAMETER_NAME"], "Value": os.environ["DATABASE_URL"], "Type": "SecureString", "Overwrite": True}, sys.stdout)' > "$SECRET_INPUT"
aws ssm put-parameter \
  --region "$REGION" \
  --cli-input-json "file://$SECRET_INPUT" \
  --output json >/dev/null
echo "SSM_DATABASE_URL_PARAMETER=CONFIGURED"

cat > "$TRUST_POLICY" <<'JSON'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }
  ]
}
JSON

if ! aws iam get-role --role-name "$ROLE_NAME" --output json >/dev/null 2>&1; then
  aws iam create-role \
    --role-name "$ROLE_NAME" \
    --assume-role-policy-document "file://$TRUST_POLICY" \
    --output json >/dev/null
  sleep 10
fi

"$PYTHON_BIN" -c 'import json, os, sys; json.dump({"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"],"Resource":"*"},{"Effect":"Allow","Action":["ssm:GetParameter"],"Resource":"*"}]}, sys.stdout)' > "$ROLE_POLICY"
aws iam put-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name OrphanProofLambdaRuntimePolicy \
  --policy-document "file://$ROLE_POLICY" \
  --output json >/dev/null

ROLE_ARN="$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)"

rm -rf "$BUILD_DIR" "$PACKAGE_PATH"
mkdir -p "$BUILD_DIR"
"$PYTHON_BIN" -m pip install \
  --upgrade \
  --target "$BUILD_DIR" \
  --platform manylinux2014_aarch64 \
  --implementation cp \
  --python-version 3.11 \
  --only-binary=:all: \
  "boto3>=1.34,<2" \
  "fastapi" \
  "mangum" \
  "mcp>=1.2,<2" \
  "pydantic" \
  "pydantic-settings" \
  "psycopg[binary]" \
  "uvicorn" >/dev/null
cp -R src/orphanproof "$BUILD_DIR/orphanproof"
if [[ ! -f "$COCKROACH_CA_CERT_SOURCE" ]]; then
  echo "COCKROACH_CA_CERT_PRESENT=False"
  echo "STOP: Public Cockroach CA certificate not found at configured local path."
  exit 1
fi
cp "$COCKROACH_CA_CERT_SOURCE" "$BUILD_DIR/cockroach-ca.crt"
echo "COCKROACH_CA_CERT_PRESENT=True"
find "$BUILD_DIR" -type d \( -name tests -o -name "__pycache__" -o -name "*.dist-info" \) -prune -exec rm -rf {} +
find "$BUILD_DIR" -name "*.pyc" -delete
cd "$BUILD_DIR"
zip -qr "../orphanproof-lambda.zip" .
cd - >/dev/null
PACKAGE_BYTES="$(wc -c < "$PACKAGE_PATH" | tr -d ' ')"
echo "LAMBDA_PACKAGE_BYTES=$PACKAGE_BYTES"

if aws lambda get-function --region "$REGION" --function-name "$FUNCTION_NAME" --output json >/dev/null 2>&1; then
  aws lambda update-function-code \
    --region "$REGION" \
    --function-name "$FUNCTION_NAME" \
    --zip-file "fileb://$PACKAGE_PATH" \
    --architectures arm64 \
    --output json >/dev/null
  aws lambda wait function-updated --region "$REGION" --function-name "$FUNCTION_NAME"
  aws lambda update-function-configuration \
    --region "$REGION" \
    --function-name "$FUNCTION_NAME" \
    --runtime python3.11 \
    --handler orphanproof.lambda_handler.handler \
    --timeout 30 \
    --memory-size 512 \
    --environment "Variables={ORPHANPROOF_ENV=production,ORPHANPROOF_BEDROCK_EMBEDDING_MODEL=local.feature-hash-v1,ORPHANPROOF_AWS_REGION=$REGION,ORPHANPROOF_DATABASE_URL_PARAMETER_NAME=$PARAMETER_NAME,ORPHANPROOF_DATABASE_SSLROOTCERT=$LAMBDA_COCKROACH_CA_CERT_PATH}" \
    --output json >/dev/null
else
  aws lambda create-function \
    --region "$REGION" \
    --function-name "$FUNCTION_NAME" \
    --runtime python3.11 \
    --role "$ROLE_ARN" \
    --handler orphanproof.lambda_handler.handler \
    --zip-file "fileb://$PACKAGE_PATH" \
    --architectures arm64 \
    --timeout 30 \
    --memory-size 512 \
    --environment "Variables={ORPHANPROOF_ENV=production,ORPHANPROOF_BEDROCK_EMBEDDING_MODEL=local.feature-hash-v1,ORPHANPROOF_AWS_REGION=$REGION,ORPHANPROOF_DATABASE_URL_PARAMETER_NAME=$PARAMETER_NAME,ORPHANPROOF_DATABASE_SSLROOTCERT=$LAMBDA_COCKROACH_CA_CERT_PATH}" \
    --output json >/dev/null
fi

aws lambda wait function-active --region "$REGION" --function-name "$FUNCTION_NAME"
if aws lambda put-function-concurrency \
  --region "$REGION" \
  --function-name "$FUNCTION_NAME" \
  --reserved-concurrent-executions 2 \
  --output json >/dev/null; then
  echo "LAMBDA_RESERVED_CONCURRENCY=2"
else
  echo "LAMBDA_RESERVED_CONCURRENCY=SKIPPED_ACCOUNT_LIMIT"
fi

if ! aws lambda get-function-url-config --region "$REGION" --function-name "$FUNCTION_NAME" --output json >/dev/null 2>&1; then
  aws lambda create-function-url-config \
    --region "$REGION" \
    --function-name "$FUNCTION_NAME" \
    --auth-type NONE \
    --cors "AllowOrigins=*,AllowMethods=GET,POST,AllowHeaders=*" \
    --output json >/dev/null
fi

aws lambda add-permission \
  --region "$REGION" \
  --function-name "$FUNCTION_NAME" \
  --statement-id FunctionURLAllowPublicInvoke \
  --action lambda:InvokeFunctionUrl \
  --principal "*" \
  --function-url-auth-type NONE \
  --output json >/dev/null 2>&1 || true

aws lambda add-permission \
  --region "$REGION" \
  --function-name "$FUNCTION_NAME" \
  --statement-id FunctionURLAllowPublicInvokeFunction \
  --action lambda:InvokeFunction \
  --principal "*" \
  --invoked-via-function-url \
  --output json >/dev/null 2>&1 || true

aws logs put-retention-policy \
  --region "$REGION" \
  --log-group-name "/aws/lambda/$FUNCTION_NAME" \
  --retention-in-days 7 \
  --output json >/dev/null 2>&1 || true

FUNCTION_URL="$(aws lambda get-function-url-config --region "$REGION" --function-name "$FUNCTION_NAME" --query FunctionUrl --output text)"
echo "FUNCTION_URL=$FUNCTION_URL"
