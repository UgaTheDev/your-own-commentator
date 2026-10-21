import 'react-native';
import {fireEvent, render} from '@testing-library/react-native';
import * as React from 'react';

import {Manifest} from '../src/manifest';
import {Home} from '../src/screens/Home';

const tr = (id: string, lang: string, kind?: 'booth') =>
  ({id, lang, kind, persona: id, label: id, src: ''} as any);
const manifest = {
  clipId: 'c',
  tracks: [
    tr('rookie-en', 'en'),
    tr('booth-en', 'en', 'booth'),
    tr('rookie-hi', 'hi'),
  ],
  highlights: {src: '', duration: 41.6},
} as unknown as Manifest;
const game = {
  clipId: 'c',
  title: 'Hazen vs Lake Region (girls varsity)',
  manifestUrl: 'https://x/m.json',
  teams: ['pink', 'blue'],
  final: {pink: 20, blue: 6},
};
const props = {
  manifest,
  error: null,
  games: [game],
  gameUrl: game.manifestUrl,
  onAirId: 'booth-en',
  onGame: jest.fn(),
  onHighlights: jest.fn(),
  onParty: jest.fn(),
  onPartyEnd: jest.fn(),
  onSelect: jest.fn(),
};

// The Vega jest preset has no BackHandler.
jest.mock('react-native', () =>
  Object.setPrototypeOf(
    {BackHandler: {addEventListener: () => ({remove: () => {}})}},
    jest.requireActual('react-native'),
  ),
);

describe('Home', () => {
  it('shows real scores, durations and the on-air commentator', () => {
    const screen = render(<Home {...props} party={null} />);
    expect(screen.getByText('PINK 20')).toBeTruthy();
    expect(screen.getByText('6 BLUE')).toBeTruthy();
    expect(screen.getByText(/42 s · every verified basket/)).toBeTruthy();
    expect(screen.getByText('Watch with Booth')).toBeTruthy();
    expect(screen.getByText('हिन्दी')).toBeTruthy();
    expect(screen.getByText(/Three AI commentators/)).toBeTruthy();
  });

  it('opens the join screen with one tile per code character', () => {
    const party = {
      code: 'AB2C7Z',
      members: [{name: 'TV', trackId: 'x', points: 1}],
      banner: null,
      send: jest.fn(),
    };
    const screen = render(<Home {...props} party={party} />);
    fireEvent.press(screen.getAllByLabelText('Watch party: AB2C7Z')[0]);
    expect(props.onParty).toHaveBeenCalled();
    'AB2C7Z'
      .split('')
      .forEach((ch) => expect(screen.getByText(ch)).toBeTruthy());
    expect(screen.getByText('1 pt')).toBeTruthy();
    fireEvent.press(screen.getByLabelText('Watch solo'));
    expect(props.onPartyEnd).toHaveBeenCalled();
    expect(props.onSelect).toHaveBeenCalledWith(manifest.tracks[1]);
  });
});
