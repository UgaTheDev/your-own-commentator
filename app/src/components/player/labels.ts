import {GameEvent} from '../../manifest';

// Points per scoring event type (pipeline event types); anything else scores nothing.
export const PTS: Record<string, number> = {ft_made: 1, made_2: 2, made_3: 3};

const PLAY: Record<string, string> = {
  made_2: 'two-pointer',
  made_3: 'three-pointer',
  ft_made: 'free throw',
  and_one: 'and-one',
};
export const playLabel = (type: string) => PLAY[type] ?? type.replace(/_/g, ' ');

const cap = (s: string) => `${s[0].toUpperCase()}${s.slice(1)}`;

// "Pink #11" / "Pink" (minors: team colour + jersey only); null without a team.
export const teamTag = (e: Pick<GameEvent, 'team' | 'jersey'>) =>
  e.team ? `${cap(e.team)}${e.jersey != null ? ` #${e.jersey}` : ''}` : null;

// "Pink #11 two-pointer", or null when the event names no team.
export const eventLabel = (e: GameEvent) => {
  const who = teamTag(e);
  return who ? `${who} ${playLabel(e.type)}` : null;
};

// The latest scoring event at most `secs` ago, as the score bug's "+N TEAM" flash.
export const flashAt = (scoring: GameEvent[], t: number, secs = 3) => {
  let last: GameEvent | null = null;
  for (const e of scoring) {
    if (e.t > t) {
      break;
    }
    last = e;
  }
  return last && last.team && t - last.t < secs
    ? {team: last.team, pts: PTS[last.type] ?? 0}
    : null;
};
