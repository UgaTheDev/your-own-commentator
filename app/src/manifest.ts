// Types mirror pipeline/publish.py build_manifest.
export type Team = 'pink' | 'blue';

export interface Track {
  id: string;
  persona: string;
  lang: string;
  label: string;
  src: string;
}

export interface GameEvent {
  id: string;
  t: number;
  type: string;
  team: Team | null;
  jersey: string | null;
  ruleCardId: string | null;
}

export interface Cue {
  t: number;
  eventId: string;
  text: string;
}

export interface GameState {
  eventId: string;
  t: number;
  score: Record<Team, number>;
  fantasy: Record<string, number>;
  andOne?: boolean;
}

export interface Manifest {
  clipId: string;
  videoUrl: string;
  tracks: Track[];
  events: GameEvent[];
  cues: Record<string, Cue[]>;
  ruleCards: Record<string, {title: string; body: string}>;
  state: GameState[];
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
  'rookie-es': 'Novato (Español)',
};
export const trackName = (tr: Track) => NAMES[tr.id] ?? tr.label;
