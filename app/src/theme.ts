import {Dimensions} from 'react-native';

// Sizes are written for a 1920x1080 TV and scaled to the device's logical width (the VVD lays out at less).
const k = Dimensions.get('window').width / 1920;
export const s = (n: number) => Math.round(n * k * 100) / 100;

// Broadcast control-room palette (after the Waterline instrument panel): quiet surfaces,
// hairline borders, one accent, team colours carry the meaning.
export const C = {
  bg: '#070b10',
  panel: '#0c1218',
  panel2: '#111922',
  glass: 'rgba(10,16,22,0.86)',
  line: '#1c2733',
  lineStrong: '#2a3847',
  text: '#e6edf3',
  muted: '#8c99a8',
  accent: '#FFD400',
  accentSoft: 'rgba(255,212,0,0.12)',
};

export const TEAM: Record<string, {bg: string; ink: string}> = {
  pink: {bg: '#d6247a', ink: '#ffffff'},
  blue: {bg: '#1f5fd6', ink: '#ffffff'},
  white: {bg: '#e6edf3', ink: '#070b10'},
  maroon: {bg: '#8c1d40', ink: '#ffffff'},
  green: {bg: '#1f8a4c', ink: '#ffffff'},
  yellow: {bg: '#f5c400', ink: '#070b10'},
};
export const team = (t: string) => TEAM[t] ?? {bg: C.lineStrong, ink: C.text};

// Small uppercase label with wide tracking, used above every section and panel.
export const eyebrow = {
  color: C.muted,
  fontSize: s(20),
  fontWeight: '700' as const,
  letterSpacing: s(4),
};
