// Types mirror pipeline/publish.py build_manifest.
export type Team = 'pink' | 'blue';

export interface Track {
  id: string;
  persona: string;
  lang: string;
  label: string;
  src: string;
  kind?: 'single' | 'booth';
  voices?: {role: 'pbp' | 'analyst'; voice: string}[];
}

export interface GameEvent {
  id: string;
  t: number;
  type: string;
  team: Team | null;
  jersey: number | null;
  ruleCardId: string | null;
}

export interface Cue {
  t: number;
  eventId: string;
  text: string;
  role?: 'pbp' | 'analyst';
}

export interface GameState {
  eventId: string;
  t: number;
  score: Record<Team, number>;
  fantasy: Record<string, number>;
  andOne?: boolean;
}

export interface Answer {
  text: string;
  audioUrl: string;
}

export interface Question {
  q: string;
  answers: Record<string, Answer>;
}

export interface Manifest {
  clipId: string;
  videoUrl: string;
  tracks: Track[];
  events: GameEvent[];
  cues: Record<string, Cue[]>;
  ruleCards: Record<string, {title: string; body: string}>;
  state: GameState[];
  // v2 (CONTRACTS.md C3), all optional so v1 manifests still load
  questions?: Record<string, Question[]>;
  replays?: {eventId: string; src: string; duration: number}[];
  minimap?: {hz: number; frames: {t: number; players: {id: number; team: Team; x: number; y: number}[]; ball: {x: number; y: number} | null}[]};
  recaps?: {t: number; src: string; text: string}[];
  talk?: {wsUrl: string};
  party?: {wsUrl: string};
}

export const fetchManifest = async (url: string): Promise<Manifest> => {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`manifest HTTP ${res.status}`);
  }
  return res.json();
};

// Last item with item.t <= t, or null. Items must be sorted by t.
export const activeAt = <T extends {t: number}>(items: T[], t: number) => {
  let lo = 0;
  let hi = items.length - 1;
  let found: T | null = null;
  while (lo <= hi) {
    const mid = Math.floor((lo + hi) / 2);
    if (items[mid].t <= t) {
      found = items[mid];
      lo = mid + 1;
    } else {
      hi = mid - 1;
    }
  }
  return found;
};

// ponytail: display names keyed by track id; falls back to the pipeline label
const NAMES: Record<string, string> = {
  'rookie-en': 'Rookie',
  'kid-en': 'Kid',
  'booth-en': 'Booth',
  'fantasy-en': 'Fantasy',
  'rookie-es': 'Novato (Español)',
  'rookie-hi': 'नौसिखिया (हिन्दी)',
  'rookie-zh': '新手 (中文)',
};
export const trackName = (tr: Track) => NAMES[tr.id] ?? tr.label;

export const WHY_WINDOW_SECS = 10;

// The latest event with questions, if it happened at most WHY_WINDOW_SECS ago.
export const whyAt = (m: Manifest, t: number) => {
  const qs = m.questions ?? {};
  const ev = activeAt(
    m.events.filter((e) => qs[e.id]?.length),
    t,
  );
  return ev && t - ev.t <= WHY_WINDOW_SECS
    ? {event: ev, questions: qs[ev.id].slice(0, 3)}
    : null;
};

// The replay of the latest event, if that event happened at most WHY_WINDOW_SECS ago.
export const replayAt = (m: Manifest, t: number) => {
  const ev = activeAt(m.events, t);
  return (
    (ev && t - ev.t <= WHY_WINDOW_SECS
      ? m.replays?.find((r) => r.eventId === ev.id)
      : undefined) ?? null
  );
};

// ponytail: the track's own answer, else any rendered one (the pipeline gates all of them)
export const answerFor = (q: Question, trackId: string): Answer | undefined =>
  q.answers[trackId] ?? Object.values(q.answers)[0];
