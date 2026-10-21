import {Dimensions} from 'react-native';

// Sizes are written for a 1920x1080 TV and scaled to the device's logical width (the VVD lays out at less).
const k = Dimensions.get('window').width / 1920;
export const s = (n: number) => Math.round(n * k * 100) / 100;

// Tokens from design/handoff/README.md (broadcast control room: quiet surfaces, hairlines, ONE accent;
// team colours only ever mean teams).
export const C = {
  bg: '#070b10',
  panel: '#0c1218',
  panel2: '#111922',
  panelFocus: '#16202b', // card while focused
  buttonFocus: '#1a2532', // button while focused
  line: '#1c2733',
  lineStrong: '#2a3847',
  text: '#e6edf3',
  textSoft: '#c4ced8',
  muted: '#8c99a8',
  accent: '#FFD400',
  accentInk: '#070b10',
  accentSoft: 'rgba(255,212,0,0.12)',
  glass: 'rgba(9,14,20,0.9)', // every overlay on video: AA without blur
  glassEdge: 'rgba(230,237,243,0.14)',
};

// Chip ink is pure white (not C.text) so pink stays AA; green darkened from #1f8a4c for AA.
export const TEAM: Record<string, {bg: string; ink: string}> = {
  pink: {bg: '#d6247a', ink: '#ffffff'},
  blue: {bg: '#1f5fd6', ink: '#ffffff'},
  white: {bg: '#e6edf3', ink: '#070b10'},
  maroon: {bg: '#8c1d40', ink: '#ffffff'},
  green: {bg: '#1a7d44', ink: '#ffffff'},
  yellow: {bg: '#f5c400', ink: '#070b10'},
};
export const team = (t: string) => TEAM[t] ?? {bg: C.lineStrong, ink: C.text};

// Type scale (px at 1920 wide). Nothing on TV is below 24.
export const T = {
  display: {fontSize: s(88), lineHeight: s(96), fontWeight: '800' as const, letterSpacing: s(-2.2)},
  h1: {fontSize: s(56), lineHeight: s(64), fontWeight: '800' as const, letterSpacing: s(-1.1)},
  h2: {fontSize: s(40), lineHeight: s(48), fontWeight: '800' as const},
  title: {fontSize: s(32), lineHeight: s(40), fontWeight: '800' as const},
  bodyL: {fontSize: s(28), lineHeight: s(40)},
  body: {fontSize: s(24), lineHeight: s(34)},
  caption: {fontSize: s(32), lineHeight: s(44), fontWeight: '600' as const},
  score: {fontSize: s(42), fontWeight: '800' as const, fontVariant: ['tabular-nums' as const]},
};

// Small uppercase label with wide tracking above sections and panels. Don't apply to Devanagari/Han text.
export const eyebrow = {
  color: C.muted,
  fontSize: s(24),
  fontWeight: '700' as const,
  letterSpacing: s(3.4),
};

// TV safe area: 96 px left/right, 54 px top/bottom.
export const SAFE = {x: s(96), y: s(54)};

export type PersonaKey =
  | 'rookie'
  | 'kid'
  | 'booth'
  | 'fantasy'
  | 'novato'
  | 'hindi'
  | 'mandarin';

// oklch tints from the handoff, converted to sRGB hex (RN has no oklch).
export const PERSONA_TINT: Record<PersonaKey, string> = {
  rookie: '#1c4159',
  kid: '#64470e',
  booth: '#3a3154',
  fantasy: '#1a463e',
  novato: '#5f3029',
  hindi: '#4f314c',
  mandarin: '#334320',
};

export const personaOf = (trackId: string): PersonaKey =>
  (
    ({
      'rookie-en': 'rookie',
      'kid-en': 'kid',
      'booth-en': 'booth',
      'fantasy-en': 'fantasy',
      'rookie-es': 'novato',
      'rookie-hi': 'hindi',
      'rookie-zh': 'mandarin',
    }) as Record<string, PersonaKey>
  )[trackId] ?? 'rookie';
