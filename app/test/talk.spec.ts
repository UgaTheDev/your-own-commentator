import {backoffMs, parseAnswer} from '../src/talk';
import {Manifest, replayAt} from '../src/manifest';

describe('talk', () => {
  it('backs off exponentially up to 30 s', () => {
    expect([0, 1, 2, 5, 9].map(backoffMs)).toEqual([
      1000, 2000, 4000, 30000, 30000,
    ]);
  });
  it('accepts only answers with HTTPS audio', () => {
    const a = {type: 'answer', text: 'x', audioUrl: 'https://c/a.mp3'};
    expect(parseAnswer(a)).toBe(a);
    expect(parseAnswer({...a, audioUrl: 'http://c/a.mp3'})).toBeNull();
    expect(parseAnswer({...a, text: 3})).toBeNull();
    expect(parseAnswer({type: 'session', code: 'ABCDEF'})).toBeNull();
  });
});

describe('replayAt', () => {
  const m = {
    events: [
      {id: 'e1', t: 10},
      {id: 'e2', t: 30},
      {id: 'e3', t: 45},
    ],
    replays: [{eventId: 'e2', src: 'https://x/r.mp4', duration: 6}],
  } as unknown as Manifest;
  it('finds the latest event replay within 10 s', () => {
    expect(replayAt(m, 40)?.src).toBe('https://x/r.mp4');
  });
  it('is null after the window or once a later event happens', () => {
    expect(replayAt(m, 40.1)).toBeNull();
    expect(replayAt(m, 46)).toBeNull();
    expect(replayAt(m, 5)).toBeNull();
  });
});
