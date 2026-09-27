# Talk-back relay: deploy runbook (Kush approves each step)

Nothing here has been run. Built and checked so far: the image (`docker build`, and a `--fake` container smoke test on
127.0.0.1), `aws cloudformation validate-template` on `template.yaml`, and the phone page against a local real relay.

Shape: phone/TV --wss--> **new CloudFront distribution** (default `*.cloudfront.net` TLS) --http:80--> ALB (its security
group only admits the CloudFront origin-facing prefix list `pl-3b927c52`) --> one Fargate ARM64 task on :8765.
Sessions are in memory, so `DesiredCount` is 0 or 1, never more. No domain and no ACM certificate are needed.

All commands run from the repo root in `us-east-1`, with account `817210752334` and the default VPC.

## 0. Once: create the stack (task count 0; this creates the ECR repo, and no task runs yet)

```sh
aws cloudformation deploy --region us-east-1 --stack-name yoc-talk \
  --template-file services/talk/template.yaml --capabilities CAPABILITY_IAM \
  --parameter-overrides VpcId=vpc-086c3219643a7793c \
    SubnetIds=subnet-08b4a9b52e458dc9f,subnet-0bc974ef3abe0af06 DesiredCount=0
aws cloudformation describe-stacks --region us-east-1 --stack-name yoc-talk \
  --query "Stacks[0].Outputs" --output table   # RepoUri, WssUrl, PhonePageUrl
```

CloudFront takes about 5 minutes to deploy. The subnets are two public default-VPC subnets in different AZs (1f and 1d).

## 1. Build and push the image

```sh
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 817210752334.dkr.ecr.us-east-1.amazonaws.com
docker build --platform linux/arm64 -f services/talk/Dockerfile \
  -t 817210752334.dkr.ecr.us-east-1.amazonaws.com/yoc-talk:latest .
docker push 817210752334.dkr.ecr.us-east-1.amazonaws.com/yoc-talk:latest
```

## 2. Publish the phone page on the existing media distribution

```sh
aws s3 cp services/talk/phone/index.html \
  s3://yoc-media-817210752334/published/talk-phone/index.html \
  --content-type text/html --cache-control no-cache
```

Open the `PhonePageUrl` output, which is
`https://d2og06dnam3owj.cloudfront.net/talk-phone/index.html?ws=wss://<relay>.cloudfront.net`. Put `WssUrl` in the
TV manifest's `talk:{wsUrl}`.

## 3. Before a demo: scale to 1 (about 1 minute until the target is healthy)

```sh
aws ecs update-service --region us-east-1 --cluster yoc-talk --service yoc-talk --desired-count 1
aws ecs wait services-stable --region us-east-1 --cluster yoc-talk --services yoc-talk
curl -s https://<relay>.cloudfront.net/healthz    # -> ok
```

After pushing a new image, add `--force-new-deployment` to the `update-service` command.

## 4. After the demo: scale to 0

```sh
aws ecs update-service --region us-east-1 --cluster yoc-talk --service yoc-talk --desired-count 0
```

(`update-service` drifts from the stack's `DesiredCount` parameter. A later `cloudformation deploy` sets the count
back to that parameter, which is 0 by default. That is the safe direction.)

## 5. After demo day: delete everything

```sh
aws cloudformation delete-stack --region us-east-1 --stack-name yoc-talk
```

The ECR repo has `EmptyOnDelete`, so the delete does not get stuck. Answer mp3s under `published/talk/` stay in the
media bucket, which this stack does not own.

## Cost (us-east-1 list prices as I recall them; check the pricing pages before relying on them)

| Item | While the stack exists | Per demo hour (1 task) |
|---|---|---|
| ALB hourly (+ under 1 LCU) | ~$0.023/h | ~$0.03 |
| Public IPv4 (ALB 2 AZs, + task) | $0.010/h | $0.015 |
| Fargate ARM64 0.5 vCPU / 1 GB | 0 at count 0 | ~$0.020 |
| CloudFront (a few MB of WebSocket traffic) | ~0 | ~0 |
| Logs, ECR storage (~200 MB image) | ~$0.02/month | ~0 |
| Per question: Sonic ASR + 2 Nova 2 Lite calls + Polly generative (~150 chars) | | ~$0.005-0.01 each |

That comes to **about $0.07 per demo hour plus about 1 cent per question**. The stack also costs **about $0.035/h
(~$0.80/day) just by existing**, because of the ALB and its IPs, so delete it after demo day (step 5).

## Security notes

- Task role: `bedrock:InvokeModelWithBidirectionalStream` on the Nova 2 Sonic model; `bedrock:InvokeModel` on the
  `us.amazon.nova-2-lite-v1:0` profile plus its three routed foundation models (us-east-1/2, us-west-2);
  `polly:SynthesizeSpeech`; `s3:PutObject` on `published/talk/*` only. The bucket is SSE-S3, so no KMS permission.
- The join rate limiter uses `YOC_PROXY_HOPS=2`: the client IP is the second-from-right X-Forwarded-For entry (the
  one CloudFront appended). The leftmost entry is whatever the client sent, so it is never trusted.
- Audio is never stored. Only the synthesized answer mp3 is written.
- Any CloudFront distribution can reach the ALB, not only ours. That lets someone bypass our CloudFront, but not the
  limits (per-session caps, and XFF still ends in the real viewer). To close it, add a secret origin header and an
  ALB listener rule.
