# Friction Log

Worth up to a 10% judging bonus. Log each friction **when it happens**: what you tried, the
exact error or confusing doc, how long it cost, and what would have fixed it. Specifics score
and vague complaints don't.

| Date | Tool / doc | What I was doing | What went wrong (exact error / link) | Time lost | Suggested fix |
|---|---|---|---|---|---|
| 2026-09-26 | AWS CLI 2.37.4 `aws login` | First CLI login on a brand-new account, run from a non-interactive shell (IDE/agent terminal) | With no region configured, `aws login` tried to prompt for one, printed `Warning: Input is not a terminal (fd=0)` and crashed with `aws: [ERROR]: [Errno 22] Invalid argument` instead of explaining that a region is required | 5 min | Fail with "No region set: pass --region or run `aws configure set region <r>`", or default the sign-in region to the one in the console URL |
| 2026-09-26 | Amazon Bedrock on a new AWS account (Free plan) | First `bedrock-runtime converse` call to `us.amazon.nova-2-lite-v1:0`, minutes after sign-up | `AccessDeniedException: Your account is currently being verified. Verification normally takes less than 2 hours.` Polly worked immediately on the same account, and `list-inference-profiles` showed Nova as ACTIVE, so nothing signalled Bedrock was blocked until the call. | Blocked up to 2 h | Show verification status in the Bedrock console/CLI (e.g. a `ModelAccess: PENDING_ACCOUNT_VERIFICATION` state), and mention it in the hackathon onboarding so builders sign up a day early |
