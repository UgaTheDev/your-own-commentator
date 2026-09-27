# Alexa+ and MCP: what we found (2026-09-27)

## MCP spec 2025-11-25 (what the server has to do)
Source: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
- Two transports: stdio and **Streamable HTTP** (one endpoint, e.g. `/mcp`, POST for every client message; GET may
  open an SSE stream or return 405). A request may be answered with `application/json` or `text/event-stream`.
- Client sends `MCP-Protocol-Version: 2025-11-25` on every request after initialize; an unsupported version gets 400.
- `MCP-Session-Id` is optional (server may be stateless). We run **stateless + JSON responses**.
- Security MUSTs: validate `Origin` (403 if present and invalid); bind to 127.0.0.1 when local; "SHOULD implement
  proper authentication".
- Tool errors: `isError: true` in the tool result (or a JSON-RPC error).

## Official Python SDK
Source: https://pypi.org/pypi/mcp/json. Current release **`mcp` 2.2.0 (2026-09-07)**, Python >= 3.10. 1.x is still
maintained (1.30.0, 2026-09-07). 2.x renamed `FastMCP` to `mcp.server.mcpserver.MCPServer`.
Verified in the installed package: `HANDSHAKE_PROTOCOL_VERSIONS = ('2024-11-05', '2025-03-26', '2025-06-18',
'2025-11-25')`, `LATEST_HANDSHAKE_VERSION = '2025-11-25'`, plus the new `2026-07-28` (discover-based) protocol.
Our live run with `Client(url, mode="legacy")` (the initialize handshake Alexa+ uses) negotiated **2025-11-25**.
The SDK auto-enables Host/Origin (DNS-rebinding) checks on 127.0.0.1: a POST with `Origin: http://evil.example` got 403.

## Alexa+ for Builders: bringing an MCP server ("MCP add-on")
Sources:
- Overview: https://developer.amazon.com/docs/alexaplus/add-ons/mcp-toolkit-overview.html
- Quickstart: https://developer.amazon.com/docs/alexaplus/add-ons/mcp-toolkit-quickstart.html
- Functional requirements: https://developer.amazon.com/docs/alexaplus/add-ons/functional-requirements.html
- Account linking: https://developer.amazon.com/docs/alexaplus/add-ons/mcp-toolkit-account-linking.html
- Certify and publish: https://developer.amazon.com/docs/alexaplus/add-ons/mcp-toolkit-certify.html
- Landing page: https://developer.amazon.com/alexaplus/

What the docs say (quoted or close paraphrase):
- "Alexa+ for Builders supports the 2025-11-25 version of the MCP specification." Must support **Streamable HTTP**;
  legacy SSE servers must migrate. **Ours: yes.**
- "Your MCP server must be accessible via a remote URL." Tunnels (cloudflared) are suggested for development.
  **Ours: local only, by rule. See DEPLOY.md.**
- Latency: quickstart says "round-trip query response latency of less than 500 ms"; functional requirements say
  "Return results within 3 seconds" and "surface an interim 'still working' message when tool calls are slow".
  **Ours:** state tools answer in 2-5 ms once the manifest is cached (the first manifest fetch took 1-3.5 s);
  `explain_play` took **1.6-2.4 s** with real Bedrock calls (writer + judge), and 3-4 ms on a cache hit.
  That meets the 3 s rule and misses the 500 ms one.
- Auth: OAuth 2.1 with PKCE (S256) account linking, needed only for user-specific data, write actions, or a
  service that requires sign-in. **Ours has no user data and no writes, so no account linking.**
- Tool guidance: every tool in `tools/list` must work; clear descriptions that map to one intent each; synonyms in
  parameter descriptions; valid `inputSchema`; accept IDs you returned earlier; errors via `isError`; voice responses
  under 30 s; at most 5 options; never refer to visuals on screenless devices. **Ours:** 5 read-only tools, spoken
  `text` of one or two sentences, lists capped at 5 in speech, clip ids from `list_games` reused by the others.
- Registration: `alexa-ai new mcp --name "..." --locale en-US --mcp-server-url "https://..."` then `alexa-ai deploy`
  (Alexa AI CLI), or the "Add-on Agent Skill" path. Package `addon-package/addon.json`: name (<= 30 chars), short
  description (<= 123), full (<= 4000), 3-4 example phrases (<= 200 each), privacy policy + terms URLs, six icon
  sizes (72x72 to 241x241) and a 600x900 carousel image. Test in the web simulator or on a device.
- "The MCP Toolkit is available in the United States."

## Unverified
- **Preview access.** The pages I read don't say whether Alexa+ for Builders needs a Preview sign-up or
  allowlist, or which account type. The quickstart points to "Set Up Your Development Environment", which I didn't read.
- **Fire TV.** Nothing I read says whether an MCP add-on can run on Alexa+ on Fire TV, or whether it can see the
  app's playhead. CONTEXT.md already lists this as unverified.
- **401 behaviour.** A search summary said an unauthenticated server "must return 401 Unauthorized (without a
  WWW-Authenticate header)". The quickstart summary read like that applies to account-linked servers. Not
  implemented. Check the account-linking page before registering.
- The Alexa AI CLI install command and version (the CLI reference page is https://developer.amazon.com/docs/alexaplus/add-ons/alexa-ai-cli-reference.html; I didn't read it).

## Design gap to settle before registering
Alexa+ doesn't know the viewer's playhead or which game is on the TV. Every tool here takes `clip_id` and `t`. On
Fire TV, `t` has to come from the TV's C4 session (the talk relay already receives `playhead{t}` every second). The
next step is probably a `session` argument that the server resolves to `{clipId, t}` through the relay. I haven't
built it: it depends on the Fire TV routing question above.

## What Kush needs to do
1. Create or sign in to an Amazon Developer account (developer.amazon.com) in the US marketplace.
2. Check whether Alexa+ for Builders / the MCP Toolkit needs a Preview request, and request it if so
   (https://developer.amazon.com/alexaplus/).
3. Install the Alexa AI CLI (see the CLI reference) and sign in.
4. Approve a public HTTPS endpoint for this server (DEPLOY.md). Until then: `cloudflared` for a dev-stage test only,
   if he approves that too.
5. Provide a privacy policy URL, a terms URL and the icon set for `addon.json` (our own art, no trademarks).
