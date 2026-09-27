const MANIFESTS = {
  fixture: 'https://d2og06dnam3owj.cloudfront.net/fixture-v2/manifest.json',
  lakeRegionDev:
    'https://d2og06dnam3owj.cloudfront.net/lake-region-dev/manifest.json',
};
// The one switch between the v2 fixture and the real clip.
export const MANIFEST_URL = MANIFESTS.lakeRegionDev;

// Dev only: drive Why / Catch me up / booth by script and log `YOC:` lines,
// since the VVD can't be screenshotted or D-padded from the CLI.
export const AUTOPILOT = false;
// Dev only: spike whether RN WebSocket works on the VVD (decides C4 transport).
export const WS_SPIKE = false;
export const WS_ECHO_URL = 'wss://ws.postman-echo.com/raw';
// Deployed services; the manifest's talk.wsUrl / party.wsUrl win when present.
// Dev relay on the Mac: 'ws://127.0.0.1:8765' through `vega device start-port-forwarding`.
export const TALK_WS_URL = 'wss://d38etaw7xiqv3j.cloudfront.net'; // C4/C5 talk relay
export const PARTY_WS_URL =
  'wss://4math2ry83.execute-api.us-east-1.amazonaws.com/dev'; // C6 watch party
