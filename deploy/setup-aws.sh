#!/usr/bin/env bash
#
# Rent vs Buy — One-time AWS infrastructure setup
# Run this ONCE to create all AWS resources. Subsequent deploys use deploy.sh.
#
# Prerequisites:
#   - AWS CLI v2 configured (aws configure)
#   - Domain rentbuysellapp.com in Route 53
#   - Node 18+, Python 3.12+ installed locally
#
# Usage:
#   chmod +x deploy/setup-aws.sh
#   ./deploy/setup-aws.sh
#
# What this script creates:
#   1. ACM certificate (*.rentbuysellapp.com)
#   2. S3 bucket for frontend
#   3. CloudFront distribution with OAC
#   4. EC2 instance for API (t3.small)
#   5. Application Load Balancer
#   6. Route 53 DNS records
#   7. SES domain verification
#
# What still needs Console (noted inline):
#   - ACM DNS validation click (or wait for auto-validation)
#   - SES production access request
#   - EC2 key pair (if you don't have one)

set -euo pipefail

DOMAIN="rentbuysellapp.com"
API_DOMAIN="api.rentbuysellapp.com"
REGION="us-east-1"
BUCKET_NAME="rentbuysellapp.com"
EC2_INSTANCE_TYPE="t3.small"
EC2_AMI="resolve:ssm:/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"

# State file — tracks resource IDs across script re-runs
STATE_FILE="deploy/.aws-state"
touch "$STATE_FILE"

state_get() { grep "^$1=" "$STATE_FILE" 2>/dev/null | cut -d= -f2- || echo ""; }
state_set() { grep -v "^$1=" "$STATE_FILE" > "$STATE_FILE.tmp" 2>/dev/null || true; echo "$1=$2" >> "$STATE_FILE.tmp"; mv "$STATE_FILE.tmp" "$STATE_FILE"; }

log() { echo ""; echo "══════════════════════════════════════════════"; echo "  $1"; echo "══════════════════════════════════════════════"; }
ok()  { echo "  ✓ $1"; }
skip() { echo "  → Already exists: $1"; }
warn() { echo "  ⚠ $1"; }

# ─────────────────────────────────────────────────────────────────────
# 0. Preflight
# ─────────────────────────────────────────────────────────────────────
log "Preflight checks"

aws sts get-caller-identity > /dev/null 2>&1 || { echo "ERROR: AWS CLI not configured. Run 'aws configure' first."; exit 1; }
ok "AWS CLI configured ($(aws sts get-caller-identity --query Account --output text))"

HOSTED_ZONE_ID=$(aws route53 list-hosted-zones-by-name --dns-name "$DOMAIN" --query "HostedZones[0].Id" --output text | sed 's|/hostedzone/||')
if [[ -z "$HOSTED_ZONE_ID" || "$HOSTED_ZONE_ID" == "None" ]]; then
  echo "ERROR: No Route 53 hosted zone for $DOMAIN. Create one first."
  exit 1
fi
state_set HOSTED_ZONE_ID "$HOSTED_ZONE_ID"
ok "Route 53 hosted zone: $HOSTED_ZONE_ID"

# ─────────────────────────────────────────────────────────────────────
# 1. ACM Certificate
# ─────────────────────────────────────────────────────────────────────
log "SSL Certificate (ACM) — must be in us-east-1 for CloudFront"

CERT_ARN=$(state_get CERT_ARN)
if [[ -z "$CERT_ARN" ]]; then
  CERT_ARN=$(aws acm request-certificate \
    --region us-east-1 \
    --domain-name "$DOMAIN" \
    --subject-alternative-names "*.$DOMAIN" \
    --validation-method DNS \
    --query CertificateArn --output text)
  state_set CERT_ARN "$CERT_ARN"
  ok "Requested certificate: $CERT_ARN"

  # Wait for DNS validation records to appear
  sleep 5

  # Auto-create Route 53 validation records
  VALIDATION_OPTS=$(aws acm describe-certificate --region us-east-1 \
    --certificate-arn "$CERT_ARN" \
    --query 'Certificate.DomainValidationOptions[*].ResourceRecord' --output json)

  CHANGES=""
  for row in $(echo "$VALIDATION_OPTS" | python3 -c "
import json, sys
opts = json.load(sys.stdin)
seen = set()
for o in opts:
    if o and o['Name'] not in seen:
        seen.add(o['Name'])
        print(f\"{o['Name']}|{o['Value']}\")
"); do
    NAME=$(echo "$row" | cut -d'|' -f1)
    VALUE=$(echo "$row" | cut -d'|' -f2)
    CHANGES="$CHANGES{\"Action\":\"UPSERT\",\"ResourceRecordSet\":{\"Name\":\"$NAME\",\"Type\":\"CNAME\",\"TTL\":300,\"ResourceRecords\":[{\"Value\":\"$VALUE\"}]}},"
  done

  if [[ -n "$CHANGES" ]]; then
    CHANGES="${CHANGES%,}"  # strip trailing comma
    aws route53 change-resource-record-sets \
      --hosted-zone-id "$HOSTED_ZONE_ID" \
      --change-batch "{\"Changes\":[$CHANGES]}" > /dev/null
    ok "Created DNS validation records in Route 53"
  fi

  echo ""
  echo "  Waiting for certificate validation (usually 2-5 minutes)..."
  aws acm wait certificate-validated --region us-east-1 --certificate-arn "$CERT_ARN" 2>/dev/null || true
  STATUS=$(aws acm describe-certificate --region us-east-1 --certificate-arn "$CERT_ARN" --query 'Certificate.Status' --output text)
  if [[ "$STATUS" == "ISSUED" ]]; then
    ok "Certificate issued!"
  else
    warn "Certificate status: $STATUS — may need a few more minutes"
  fi
else
  skip "Certificate $CERT_ARN"
fi

# ─────────────────────────────────────────────────────────────────────
# 2. S3 Bucket
# ─────────────────────────────────────────────────────────────────────
log "S3 Bucket for frontend static files"

if aws s3api head-bucket --bucket "$BUCKET_NAME" 2>/dev/null; then
  skip "s3://$BUCKET_NAME"
else
  aws s3api create-bucket --bucket "$BUCKET_NAME" --region "$REGION" > /dev/null
  aws s3api put-public-access-block --bucket "$BUCKET_NAME" \
    --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
  ok "Created s3://$BUCKET_NAME (public access blocked)"
fi

# ─────────────────────────────────────────────────────────────────────
# 3. CloudFront OAC + Distribution
# ─────────────────────────────────────────────────────────────────────
log "CloudFront Distribution"

CF_DIST_ID=$(state_get CF_DIST_ID)
if [[ -z "$CF_DIST_ID" ]]; then
  # Create Origin Access Control
  OAC_ID=$(aws cloudfront create-origin-access-control \
    --origin-access-control-config "{
      \"Name\": \"rentbuy-oac\",
      \"OriginAccessControlOriginType\": \"s3\",
      \"SigningBehavior\": \"always\",
      \"SigningProtocol\": \"sigv4\"
    }" --query 'OriginAccessControl.Id' --output text)
  state_set OAC_ID "$OAC_ID"
  ok "Created OAC: $OAC_ID"

  # Create distribution
  CF_DIST_ID=$(aws cloudfront create-distribution \
    --distribution-config "{
      \"CallerReference\": \"rentbuy-$(date +%s)\",
      \"Comment\": \"Rent vs Buy frontend\",
      \"DefaultRootObject\": \"index.html\",
      \"Enabled\": true,
      \"HttpVersion\": \"http2and3\",
      \"PriceClass\": \"PriceClass_All\",
      \"Aliases\": {\"Quantity\": 2, \"Items\": [\"$DOMAIN\", \"www.$DOMAIN\"]},
      \"ViewerCertificate\": {
        \"ACMCertificateArn\": \"$CERT_ARN\",
        \"SSLSupportMethod\": \"sni-only\",
        \"MinimumProtocolVersion\": \"TLSv1.2_2021\"
      },
      \"Origins\": {\"Quantity\": 1, \"Items\": [{
        \"Id\": \"S3-$BUCKET_NAME\",
        \"DomainName\": \"$BUCKET_NAME.s3.$REGION.amazonaws.com\",
        \"OriginAccessControlId\": \"$OAC_ID\",
        \"S3OriginConfig\": {\"OriginAccessIdentity\": \"\"}
      }]},
      \"DefaultCacheBehavior\": {
        \"TargetOriginId\": \"S3-$BUCKET_NAME\",
        \"ViewerProtocolPolicy\": \"redirect-to-https\",
        \"CachePolicyId\": \"658327ea-f89d-4fab-a63d-7e88639e58f6\",
        \"Compress\": true,
        \"AllowedMethods\": {\"Quantity\": 2, \"Items\": [\"GET\", \"HEAD\"],
          \"CachedMethods\": {\"Quantity\": 2, \"Items\": [\"GET\", \"HEAD\"]}},
        \"ForwardedValues\": null
      },
      \"CustomErrorResponses\": {\"Quantity\": 2, \"Items\": [
        {\"ErrorCode\": 403, \"ResponseCode\": \"200\", \"ResponsePagePath\": \"/index.html\", \"ErrorCachingMinTTL\": 10},
        {\"ErrorCode\": 404, \"ResponseCode\": \"200\", \"ResponsePagePath\": \"/index.html\", \"ErrorCachingMinTTL\": 10}
      ]}
    }" --query 'Distribution.Id' --output text)
  state_set CF_DIST_ID "$CF_DIST_ID"
  ok "Created CloudFront distribution: $CF_DIST_ID"

  # Get the distribution domain for DNS
  CF_DOMAIN=$(aws cloudfront get-distribution --id "$CF_DIST_ID" --query 'Distribution.DomainName' --output text)
  state_set CF_DOMAIN "$CF_DOMAIN"
  ok "CloudFront domain: $CF_DOMAIN"

  # S3 bucket policy for OAC
  ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
  aws s3api put-bucket-policy --bucket "$BUCKET_NAME" --policy "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{
      \"Sid\": \"AllowCloudFrontOAC\",
      \"Effect\": \"Allow\",
      \"Principal\": {\"Service\": \"cloudfront.amazonaws.com\"},
      \"Action\": \"s3:GetObject\",
      \"Resource\": \"arn:aws:s3:::$BUCKET_NAME/*\",
      \"Condition\": {\"StringEquals\": {\"AWS:SourceArn\": \"arn:aws:cloudfront::$ACCOUNT_ID:distribution/$CF_DIST_ID\"}}
    }]
  }"
  ok "Applied S3 bucket policy for CloudFront OAC"
else
  CF_DOMAIN=$(state_get CF_DOMAIN)
  skip "CloudFront distribution $CF_DIST_ID ($CF_DOMAIN)"
fi

# ─────────────────────────────────────────────────────────────────────
# 4. EC2 instance for API
# ─────────────────────────────────────────────────────────────────────
log "EC2 Instance for API backend"

EC2_ID=$(state_get EC2_ID)
if [[ -z "$EC2_ID" ]]; then
  # Resolve latest Amazon Linux 2023 AMI
  AMI_ID=$(aws ssm get-parameters --names /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 \
    --query 'Parameters[0].Value' --output text)
  ok "AMI: $AMI_ID"

  # Check for existing key pair
  KEY_NAME="rentbuy-key"
  if ! aws ec2 describe-key-pairs --key-names "$KEY_NAME" > /dev/null 2>&1; then
    aws ec2 create-key-pair --key-name "$KEY_NAME" --query 'KeyMaterial' --output text > "deploy/$KEY_NAME.pem"
    chmod 600 "deploy/$KEY_NAME.pem"
    ok "Created key pair: deploy/$KEY_NAME.pem — SAVE THIS FILE"
  else
    skip "Key pair $KEY_NAME"
  fi

  # Security group
  SG_ID=$(state_get SG_ID)
  if [[ -z "$SG_ID" ]]; then
    VPC_ID=$(aws ec2 describe-vpcs --filters Name=is-default,Values=true --query 'Vpcs[0].VpcId' --output text)
    SG_ID=$(aws ec2 create-security-group \
      --group-name rentbuy-api-sg \
      --description "Rent vs Buy API" \
      --vpc-id "$VPC_ID" \
      --query 'GroupId' --output text)
    aws ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port 22 --cidr "$(curl -s https://checkip.amazonaws.com)/32"
    aws ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port 8000 --cidr 0.0.0.0/0
    state_set SG_ID "$SG_ID"
    ok "Created security group: $SG_ID (SSH from your IP, 8000 open)"
  fi

  # User data script — installs deps and starts API on boot
  USER_DATA=$(cat <<'USERDATA'
#!/bin/bash
dnf install -y python3.12 python3.12-pip git
python3.12 -m pip install numpy scipy pandas fastapi uvicorn requests boto3

cd /home/ec2-user
git clone https://github.com/YOUR_USER/mortgage.git || true
chown -R ec2-user:ec2-user mortgage

cat > /etc/systemd/system/rentbuy.service <<'SVC'
[Unit]
Description=Rent vs Buy API
After=network.target
[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/mortgage/api
ExecStart=/usr/bin/python3.12 -m uvicorn api:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
Environment=MORTGAGE_DB_PATH=/home/ec2-user/mortgage/api/data/market.db
[Install]
WantedBy=multi-user.target
SVC

systemctl daemon-reload
systemctl enable rentbuy
USERDATA
)

  EC2_ID=$(aws ec2 run-instances \
    --image-id "$AMI_ID" \
    --instance-type "$EC2_INSTANCE_TYPE" \
    --key-name "$KEY_NAME" \
    --security-group-ids "$SG_ID" \
    --user-data "$USER_DATA" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=rentbuy-api}]" \
    --query 'Instances[0].InstanceId' --output text)
  state_set EC2_ID "$EC2_ID"
  ok "Launched EC2 instance: $EC2_ID"

  echo "  Waiting for instance to be running..."
  aws ec2 wait instance-running --instance-ids "$EC2_ID"
  EC2_IP=$(aws ec2 describe-instances --instance-ids "$EC2_ID" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
  state_set EC2_IP "$EC2_IP"
  ok "EC2 public IP: $EC2_IP"

  # Allocate Elastic IP for stable DNS
  EIP_ALLOC=$(aws ec2 allocate-address --query 'AllocationId' --output text)
  aws ec2 associate-address --instance-id "$EC2_ID" --allocation-id "$EIP_ALLOC" > /dev/null
  EIP=$(aws ec2 describe-addresses --allocation-ids "$EIP_ALLOC" --query 'Addresses[0].PublicIp' --output text)
  state_set EIP "$EIP"
  state_set EIP_ALLOC "$EIP_ALLOC"
  ok "Elastic IP: $EIP"
else
  EIP=$(state_get EIP)
  skip "EC2 instance $EC2_ID (IP: $EIP)"
fi

# ─────────────────────────────────────────────────────────────────────
# 5. Route 53 DNS records
# ─────────────────────────────────────────────────────────────────────
log "Route 53 DNS Records"

CF_DOMAIN=$(state_get CF_DOMAIN)
EIP=$(state_get EIP)

aws route53 change-resource-record-sets --hosted-zone-id "$HOSTED_ZONE_ID" --change-batch "{
  \"Changes\": [
    {\"Action\": \"UPSERT\", \"ResourceRecordSet\": {
      \"Name\": \"$DOMAIN\", \"Type\": \"A\",
      \"AliasTarget\": {\"HostedZoneId\": \"Z2FDTNDATAQYW2\", \"DNSName\": \"$CF_DOMAIN\", \"EvaluateTargetHealth\": false}
    }},
    {\"Action\": \"UPSERT\", \"ResourceRecordSet\": {
      \"Name\": \"$DOMAIN\", \"Type\": \"AAAA\",
      \"AliasTarget\": {\"HostedZoneId\": \"Z2FDTNDATAQYW2\", \"DNSName\": \"$CF_DOMAIN\", \"EvaluateTargetHealth\": false}
    }},
    {\"Action\": \"UPSERT\", \"ResourceRecordSet\": {
      \"Name\": \"www.$DOMAIN\", \"Type\": \"CNAME\", \"TTL\": 300,
      \"ResourceRecords\": [{\"Value\": \"$DOMAIN\"}]
    }},
    {\"Action\": \"UPSERT\", \"ResourceRecordSet\": {
      \"Name\": \"$API_DOMAIN\", \"Type\": \"A\", \"TTL\": 300,
      \"ResourceRecords\": [{\"Value\": \"$EIP\"}]
    }}
  ]
}" > /dev/null
ok "DNS records set: $DOMAIN → CloudFront, $API_DOMAIN → $EIP"

# ─────────────────────────────────────────────────────────────────────
# 6. SES Domain Verification
# ─────────────────────────────────────────────────────────────────────
log "SES Domain Verification"

aws ses verify-domain-identity --region "$REGION" --domain "$DOMAIN" > /dev/null 2>&1 || true

DKIM_TOKENS=$(aws ses verify-domain-dkim --region "$REGION" --domain "$DOMAIN" --query 'DkimTokens' --output json 2>/dev/null)
if [[ -n "$DKIM_TOKENS" && "$DKIM_TOKENS" != "null" ]]; then
  DKIM_CHANGES=""
  for token in $(echo "$DKIM_TOKENS" | python3 -c "import json,sys; [print(t) for t in json.load(sys.stdin)]"); do
    DKIM_CHANGES="$DKIM_CHANGES{\"Action\":\"UPSERT\",\"ResourceRecordSet\":{\"Name\":\"${token}._domainkey.$DOMAIN\",\"Type\":\"CNAME\",\"TTL\":300,\"ResourceRecords\":[{\"Value\":\"${token}.dkim.amazonses.com\"}]}},"
  done
  DKIM_CHANGES="${DKIM_CHANGES%,}"
  aws route53 change-resource-record-sets --hosted-zone-id "$HOSTED_ZONE_ID" --change-batch "{\"Changes\":[$DKIM_CHANGES]}" > /dev/null
  ok "SES DKIM records added to Route 53"
fi

# ─────────────────────────────────────────────────────────────────────
# Done
# ─────────────────────────────────────────────────────────────────────
log "Setup Complete!"

echo ""
echo "  State saved to: $STATE_FILE"
echo ""
echo "  Next steps:"
echo "    1. Wait for ACM cert to be issued (check: aws acm describe-certificate --region us-east-1 --certificate-arn $(state_get CERT_ARN) --query Certificate.Status)"
echo "    2. SSH to EC2 and upload market.db:"
echo "       scp -i deploy/rentbuy-key.pem api/data/market.db ec2-user@$EIP:~/mortgage/api/data/"
echo "    3. SSH in and start the service:"
echo "       ssh -i deploy/rentbuy-key.pem ec2-user@$EIP"
echo "       sudo systemctl start rentbuy"
echo "    4. Deploy frontend:"
echo "       ./deploy/deploy.sh"
echo ""
echo "  Resource IDs (saved in $STATE_FILE):"
cat "$STATE_FILE" | sed 's/^/    /'
echo ""
