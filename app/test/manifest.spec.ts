import {Manifest, activeAt, answerFor, whyAt} from '../src/manifest';

const q = (id: string) => ({
  q: `why ${id}`,
  answers: {'rookie-en': {text: `a ${id}`, audioUrl: `https://x/${id}.mp3`}},
});
const m = {
  events: [
    {id: 'e1', t: 10},
    {id: 'e2', t: 30},
    {id: 'e3', t: 35},
  ],
  questions: {e1: [q('1a'), q('1b'), q('1c'), q('1d')], e2: [q('2a')]},
} as unknown as Manifest;

describe('whyAt', () => {
  it('is null before any event with questions', () => {
    expect(whyAt(m, 5)).toBeNull();
  });
  it('caps at 3 questions', () => {
    expect(whyAt(m, 12)?.questions).toHaveLength(3);
  });
  it('allows exactly the 10 s window', () => {
    expect(whyAt(m, 20)?.event.id).toBe('e1');
    expect(whyAt(m, 20.1)).toBeNull();
  });
  it('skips later events without questions', () => {
    expect(whyAt(m, 36)?.event.id).toBe('e2');
  });
  it('is null when the manifest has no questions', () => {
    expect(whyAt({...m, questions: undefined}, 12)).toBeNull();
  });
});

describe('answerFor', () => {
  it('prefers the current track, else falls back', () => {
    const two = {
      q: 'x',
      answers: {a: {text: 'A', audioUrl: ''}, b: {text: 'B', audioUrl: ''}},
    };
    expect(answerFor(two, 'b')?.text).toBe('B');
    expect(answerFor(two, 'zz')?.text).toBe('A');
  });
});

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
