import 'react-native';
import {render} from '@testing-library/react-native';
import * as React from 'react';

import {App} from '../src/App';

jest.mock('@amazon-devices/react-native-w3cmedia', () => ({}));

describe('App', () => {
  it('renders the home title while the manifest loads', () => {
    // eslint-disable-next-line no-undef
    globalThis.fetch = jest.fn(() => new Promise(() => {})) as jest.Mock;
    const screen = render(<App />);
    expect(screen.getByText('Your Own Commentator')).toBeTruthy();
  });
});
