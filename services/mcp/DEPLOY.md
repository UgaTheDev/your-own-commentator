# MCP server: deploy plan (NOT deployed; Kush approves each step)

Today it runs only locally: `python services/mcp/yoc_mcp.py` (stdio) or `--http` (http://127.0.0.1:8790/mcp).
Alexa+ needs a public HTTPS URL that speaks Streamable HTTP (see ALEXA.md).

## Recommended: Lambda + Lambda Web Adapter + function URL
Why: the server is stateless (`stateless_http=True, json_response=True`). No sessions or SSE means it fits
request/response Lambda, costs nothing while idle, and needs no ALB (~$0.80/day just to exist in the talk stack).
Lambda Web Adapter runs the same uvicorn app unchanged, so there's no new code or ASGI shim.

Shape: Alexa+ --HTTPS--> Lambda function URL (auth NONE; public by design, since the add-on has no account
linking) --> Lambda (Python 3.13, arm64, 1 GB, 10 s timeout, Web Adapter layer, `PORT=8790`) --> CloudFront
manifests + Bedrock `Converse` (write + judge models from `pipeline/common.MODELS`).

Changes needed before deploy (small, in services/mcp only):
- Bind `0.0.0.0` inside Lambda (behind the adapter), and set the SDK's `TransportSecuritySettings` `allowed_hosts`
  to the function URL host. The localhost DNS-rebinding defaults would otherwise reject the real Host header.
- Put the data and cache dirs that `pipeline/common` writes under `/tmp` (Lambda's only writable path).
- Reserved concurrency (for example 5) as a cost and abuse cap. `explain_play` is the only paid call (2 Bedrock calls).

Steps Kush would approve:
1. `sam build` / `sam deploy --guided` for a `template.yaml` with the function, the Web Adapter layer
   (`arn:aws:lambda:us-east-1:753240598075:layer:LambdaAdapterLayerArm64:<ver>`: verify the ARN and current version),
   a function URL, and an IAM role with only `bedrock:InvokeModel` on the two inference profiles plus CloudWatch Logs.
2. Smoke test: `python services/mcp/tests/live_http.py https://<id>.lambda-url.us-east-1.on.aws/mcp`.
3. Register: `alexa-ai new mcp --name "Your Own Commentator" --locale en-US --mcp-server-url https://<id>.lambda-url.us-east-1.on.aws/mcp`
   then `alexa-ai deploy` (development stage only; no certification).
4. Test in the Alexa+ web simulator.
5. After the hackathon: `sam delete`.

Latency: a cold start (Python + mcp + boto3) likely costs 1-2 s (unmeasured). If the demo needs it, set provisioned
concurrency to 1 for the demo hour only. `explain_play` is 1.6-2.4 s warm because of Bedrock, so it meets Alexa's
"within 3 seconds" and misses the quickstart's "< 500 ms". To get under 500 ms, answer from the manifest's
pre-rendered `questions` when the question matches one, and only call `answer()` otherwise.

## Alternative: next to the talk relay (Fargate + ALB + CloudFront)
Run `yoc_mcp.py --http` as a second process or container in the `yoc-talk` task. Add an ALB listener rule
`/mcp*` to it and a CloudFront behavior `/mcp*` (no caching, all methods, forward `MCP-Protocol-Version` and
`Content-Type`). It reuses the existing stack, but it's only up while the relay is scaled to 1, and the ALB costs
money even at 0 tasks. Use it if we'd rather have one stack than two.

## Auth
No account linking, because the tools read public game data only. Hardening for the public URL: input limits already
in the tools (clip-id regex, 0 <= t <= 7200, question <= 300 chars, known persona), reserved concurrency, and an AWS
Budgets alert. Check ALEXA.md's "401 behaviour" item before registering. If Alexa+ requires a bearer token even
without linking, verify it with the SDK's `token_verifier` hook rather than custom middleware.
