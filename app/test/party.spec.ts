import {gainers, newCode, parseResolve, parseState} from '../src/party';
import {Track, trackName} from '../src/manifest';

const tr = (id: string, label: string) => ({id, label} as Track);

describe('party', () => {
  it('makes 6-char base32 codes the backend accepts', () => {
    expect(newCode()).toMatch(/^[A-Z2-7]{6}$/);
    expect(newCode(() => 0.9999)).toBe('777777');
  });
  it('names who scored between two states', () => {
    const a = [
      {name: 'TV', trackId: 'r', points: 0},
      {name: 'Friend', trackId: 'r', points: 1},
    ];
    const b = [
      {name: 'TV', trackId: 'r', points: 0},
      {name: 'Friend', trackId: 'r', points: 2},
    ];
    expect(gainers(a, b)).toEqual(['Friend']);
    expect(gainers(b, b)).toEqual([]);
    expect(gainers([], [{name: 'New', trackId: 'r', points: 1}])).toEqual([
      'New',
    ]);
  });
  it('drops malformed messages', () => {
    expect(
      parseState({
        type: 'state',
        members: [{name: 'A', points: 'x'}, {points: 3}],
      }),
    ).toEqual([{name: 'A', trackId: '', points: 0}]);
    expect(parseState({type: 'resolve'})).toBeNull();
    const r = {type: 'resolve', predictionId: 'p', correct: true, eventId: 'e'};
    expect(parseResolve(r)).toBe(r);
    expect(parseResolve({...r, correct: 'yes'})).toBeNull();
  });
  it('labels the Hindi and Chinese tracks in their own script', () => {
    expect(trackName(tr('rookie-hi', 'Rookie (HI)'))).toBe('नौसिखिया (हिन्दी)');
    expect(trackName(tr('rookie-zh', 'Rookie (ZH)'))).toBe('新手 (中文)');
    expect(trackName(tr('new-x', 'New (X)'))).toBe('New (X)');
  });
});
