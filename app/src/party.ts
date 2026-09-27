// C6 watch-party client: join a room, forward predict/playhead, report state and resolve.
import {backoffMs} from './talk';

export interface Member {
  name: string;
  trackId: string;
  points: number;
}

export interface Resolve {
  predictionId: string;
  correct: boolean;
  eventId: string;
}

const ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
// ponytail: Math.random is fine for a party room (no secrets behind it); the backend accepts any ^[A-Z2-7]{6}$
export const newCode = (rnd = Math.random) =>
  Array.from({length: 6}, () => ALPHABET[Math.floor(rnd() * 32)]).join('');

// Untrusted input from the network: keep only well-formed members.
export const parseState = (msg: any): Member[] | null =>
  msg?.type === 'state' && Array.isArray(msg.members)
    ? msg.members
        .filter((m: any) => typeof m?.name === 'string')
        .map((m: any) => ({
          name: m.name.slice(0, 32),
          trackId: String(m.trackId ?? ''),
          points: Number.isFinite(m.points) ? m.points : 0,
        }))
    : null;

export const parseResolve = (msg: any): Resolve | null =>
  msg?.type === 'resolve' &&
  typeof msg.predictionId === 'string' &&
  typeof msg.correct === 'boolean' &&
  typeof msg.eventId === 'string'
    ? msg
    : null;

// Names whose points went up between two states (resolve carries no name, so the state diff says who scored).
export const gainers = (prev: Member[], next: Member[]) => {
  const before = new Map(prev.map((m) => [m.name, m.points]));
  return next
    .filter((m) => m.points > (before.get(m.name) ?? 0))
    .map((m) => m.name);
};

interface Opts {
  url: string;
  code: string;
  name: string;
  trackId: string;
  clipId: string;
  onState: (members: Member[]) => void;
  onResolve: (r: Resolve) => void;
  log: (msg: string) => void;
}

// Returns send/stop. Reconnects (and re-joins) with exponential backoff until stopped.
export const connectParty = (o: Opts) => {
  let ws: WebSocket | null = null;
  let retry = 0;
  let fails = 0;
  let stopped = false;

  const open = () => {
    const s = new WebSocket(o.url);
    const started = Date.now();
    ws = s;
    s.onopen = () => {
      fails = 0;
      o.log(`party open after ${Date.now() - started}ms, join ${o.code}`);
      s.send(
        JSON.stringify({
          type: 'join',
          code: o.code,
          name: o.name,
          trackId: o.trackId,
          clipId: o.clipId,
        }),
      );
    };
    s.onmessage = (e) => {
      let msg: any;
      try {
        msg = JSON.parse(String(e.data));
      } catch {
        return;
      }
      const members = parseState(msg);
      if (members) {
        o.log(
          `party state ${members
            .map((m) => `${m.name}=${m.points}`)
            .join(' ')}`,
        );
        o.onState(members);
        return;
      }
      const r = parseResolve(msg);
      if (r) {
        o.log(`party resolve ${r.predictionId} correct=${r.correct} ${r.eventId}`);
        o.onResolve(r);
      }
    };
    s.onerror = (e: any) => o.log(`party error ${e?.message ?? ''}`);
    s.onclose = (e) => {
      if (stopped) {
        return;
      }
      const ms = backoffMs(fails++);
      o.log(`party closed code=${e.code}, retry in ${ms}ms`);
      retry = setTimeout(open, ms);
    };
  };

  open();
  return {
    send: (msg: object) => {
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(msg));
      }
    },
    stop: () => {
      stopped = true;
      clearTimeout(retry);
      ws?.close();
    },
  };
};

export type Party = ReturnType<typeof connectParty>;
