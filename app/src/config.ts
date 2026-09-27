const MANIFESTS = {
  fixture: 'https://d2og06dnam3owj.cloudfront.net/fixture-v2/manifest.json',
  lakeRegionDev:
    'https://d2og06dnam3owj.cloudfront.net/lake-region-dev/manifest.json',
};
// The one switch between the v2 fixture and the real clip.
export const MANIFEST_URL = MANIFESTS.fixture;

// Dev only: drive Why / Catch me up / booth by script and log `YOC:` lines,
// since the VVD can't be screenshotted or D-padded from the CLI.
export const AUTOPILOT = false;
// Dev only: spike whether RN WebSocket works on the VVD (decides C4 transport).
export const WS_SPIKE = false;
export const WS_ECHO_URL = 'wss://ws.postman-echo.com/raw';
// C4 talk relay (services/talk/server.py). The manifest's talk.wsUrl wins when deployed.
// Dev: the VVD reaches the Mac's 127.0.0.1:8765 through `vega device start-port-forwarding`.
export const TALK_WS_URL = 'ws://127.0.0.1:8765';
