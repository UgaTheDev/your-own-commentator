import {eventLabel, flashAt, teamTag} from '../src/components/player/labels';

const ev = (
  t: number,
  type: string,
  team: string | null,
  jersey: number | null,
) => ({
  id: `e${t}`,
  t,
  type,
  team,
  jersey,
  ruleCardId: null,
});

describe('player labels', () => {
  it('names teams and jerseys only when present', () => {
    expect(teamTag({team: 'pink', jersey: 11})).toBe('Pink #11');
    expect(teamTag({team: 'blue', jersey: null})).toBe('Blue');
    expect(teamTag({team: null, jersey: 4})).toBeNull();
    expect(eventLabel(ev(1, 'made_2', 'pink', 11))).toBe(
      'Pink #11 two-pointer',
    );
    expect(eventLabel(ev(1, 'travel', null, null))).toBeNull();
  });

  it('flashes the latest basket for 3 s with its points', () => {
    const scoring = [
      ev(10, 'made_3', 'pink', 5),
      ev(20, 'ft_made', 'blue', null),
    ];
    expect(flashAt(scoring, 9)).toBeNull();
    expect(flashAt(scoring, 11)).toEqual({team: 'pink', pts: 3});
    expect(flashAt(scoring, 13.5)).toBeNull();
    expect(flashAt(scoring, 21)).toEqual({team: 'blue', pts: 1});
  });
});
