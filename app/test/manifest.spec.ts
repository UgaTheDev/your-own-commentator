import {activeAt} from '../src/manifest';

const items = [{t: 1}, {t: 5}, {t: 9}];

describe('activeAt', () => {
  it('is null before the first item', () => {
    expect(activeAt(items, 0.5)).toBeNull();
  });
  it('matches exactly on t', () => {
    expect(activeAt(items, 5)).toBe(items[1]);
  });
  it('returns the earlier item between two', () => {
    expect(activeAt(items, 7)).toBe(items[1]);
  });
  it('returns the last item after the end', () => {
    expect(activeAt(items, 100)).toBe(items[2]);
  });
  it('is null for an empty list', () => {
    expect(activeAt([], 3)).toBeNull();
  });
});
