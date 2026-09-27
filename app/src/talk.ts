// C4 client: pair with the talk relay, stream the playhead every 1 s, hand answers to the Player.
export interface TalkAnswer {
  id?: string;
  t?: number;
  text: string;
  audioUrl: string;
  voice?: string;
}

export interface Playhead {
  t: number;
  trackId: string;
  paused: boolean;
}

interface Opts {
  url: string;
  clipId: string;
  playhead: () => Playhead;
  onCode: (code: string | null) => void;
  onAnswer: (a: TalkAnswer) => void;
  log: (msg: string) => void;
}

export const backoffMs = (fails: number) => Math.min(30000, 1000 * 2 ** fails);

// Untrusted input from the network: only a well-formed answer with HTTPS audio gets through.
export const parseAnswer = (msg: any): TalkAnswer | null =>
  msg?.type === 'answer' &&
  typeof msg.text === 'string' &&
  typeof msg.audioUrl === 'string' &&
  msg.audioUrl.startsWith('https://')
    ? msg
    : null;

// Returns a stop function. Reconnects with exponential backoff until stopped.
export const connectTalk = (o: Opts) => {
  let ws: WebSocket | null = null;
  let tick = 0;
  let retry = 0;
  let fails = 0;
  let sent = 0;
  let stopped = false;

  const open = () => {
    const s = new WebSocket(o.url);
    const started = Date.now();
    ws = s;
    s.onopen = () => {
      o.log(`talk open ${o.url} after ${Date.now() - started}ms`);
      s.send(JSON.stringify({type: 'hello', clipId: o.clipId}));
    };
    s.onmessage = (e) => {
      let msg: any;
      try {
        msg = JSON.parse(String(e.data));
      } catch {
        return;
      }
      if (msg?.type === 'session' && typeof msg.code === 'string') {
        fails = 0;
        o.onCode(msg.code);
        o.log(`talk session code=${msg.code}`);
        clearInterval(tick);
        tick = setInterval(() => {
          if (s.readyState !== WebSocket.OPEN) {
            return;
          }
          const p = o.playhead();
          const t = Math.max(0, Number.isFinite(p.t) ? p.t : 0);
          s.send(JSON.stringify({type: 'playhead', ...p, t}));
          if (++sent % 10 === 1) {
            o.log(`talk playhead #${sent} t=${t.toFixed(2)} ${p.trackId} paused=${p.paused}`);
          }
        }, 1000);
        return;
      }
      const a = parseAnswer(msg);
      if (a) {
        o.log(`talk answer ${a.id ?? '?'} t=${a.t} "${a.text}" -> ${a.audioUrl}`);
        o.onAnswer(a);
      }
    };
    s.onerror = (e: any) => o.log(`talk error ${e?.message ?? ''}`);
    s.onclose = (e) => {
      clearInterval(tick);
      if (stopped) {
        return;
      }
      o.onCode(null);
      const ms = backoffMs(fails++);
      o.log(`talk closed code=${e.code} "${e.reason ?? ''}", retry in ${ms}ms`);
      retry = setTimeout(open, ms);
    };
  };

  open();
  return () => {
    stopped = true;
    clearTimeout(retry);
    clearInterval(tick);
    ws?.close();
  };
};
