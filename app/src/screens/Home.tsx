import React, {useRef, useState} from 'react';
import {Image, ScrollView, StyleSheet, Text, View} from 'react-native';
import {Mark, PersonaIcon, Wordmark} from '../components/Brand';
import {FocusButton} from '../components/FocusButton';
import {Game, Manifest, Track, trackName, trackTagline} from '../manifest';
import {Member} from '../party';
import {C, SAFE, T, eyebrow, personaOf, s, team} from '../theme';
import {PartyJoin} from './PartyJoin';

export interface PartyView {
  code: string;
  members: Member[];
  banner: string | null;
  send: (msg: object) => void;
}

interface Props {
  manifest: Manifest | null;
  error: string | null;
  party: PartyView | null;
  games: Game[];
  gameUrl: string;
  onAirId: string | null; // last commentator picked; the first track until then
  onGame: (manifestUrl: string) => void;
  onHighlights: () => void;
  onParty: () => void;
  onPartyEnd: () => void;
  onSelect: (track: Track) => void;
}

// Card name without the bracketed language: the chip under it says that.
const shortName = (tr: Track) => trackName(tr).replace(/\s*\(.*\)$/, '');
// "Hazen vs X (girls varsity)" -> ["Hazen vs X", "GIRLS VARSITY"]
const splitTitle = (t: string) => {
  const m = t.match(/^(.*?)\s*\((.*)\)$/);
  return m ? [m[1], m[2].toUpperCase()] : [t, ''];
};
const vs = (g?: Game) =>
  g?.teams?.length
    ? g.teams.map((t) => t.toUpperCase()).join(' VS ')
    : splitTitle(g?.title ?? '')[0].toUpperCase();

// Never letter-space or uppercase these: Devanagari and Han are written as is.
const LANG: Record<string, string> = {
  en: 'ENGLISH',
  es: 'ESPAÑOL',
  hi: 'हिन्दी',
  zh: '中文',
};
// Handoff 2b copy. Fantasy's handoff line ("streaks", "heating up") claims more than the track says.
const TAGLINES: Record<string, string> = {
  'rookie-en': 'Every call explained, zero jargon.',
  'kid-en': 'Big plays, big feelings, small words.',
  'booth-en':
    'The classic two-person broadcast: one calls it, one breaks it down.',
  'fantasy-en': 'Fantasy points on every basket.',
  'rookie-es': 'Cada jugada, explicada desde cero.',
  'rookie-hi': 'हर नियम, आसान शब्दों में।',
  'rookie-zh': '每个判罚，简单讲清楚。',
};
const NUM = [
  'No',
  'One',
  'Two',
  'Three',
  'Four',
  'Five',
  'Six',
  'Seven',
  'Eight',
  'Nine',
  'Ten',
];

// No gradient lib on Vega: a CSS linear-gradient becomes BANDS bands of bg at alpha(p), p = 0..1 along the axis.
const BANDS = 64; // 24 showed visible steps on the VVD
const Fade = ({
  alpha,
  down,
}: {
  alpha: (p: number) => number;
  down?: boolean;
}) => (
  <View
    pointerEvents="none"
    style={[StyleSheet.absoluteFill, down ? styles.col : styles.split]}>
    {Array.from({length: BANDS}, (_, i) => (
      <View
        key={i}
        style={[
          styles.flex,
          {
            backgroundColor: `rgba(7,11,16,${alpha((i + 0.5) / BANDS).toFixed(
              3,
            )})`,
          },
        ]}
      />
    ))}
  </View>
);
// 90deg: #070b10 0% -> .75 at 30% -> 0 at 70%;  180deg: 0 at 55% -> #070b10 100%.
const heroSide = (p: number) =>
  p < 0.3 ? 1 - (0.25 * p) / 0.3 : p < 0.7 ? 0.75 * (1 - (p - 0.3) / 0.4) : 0;
const heroBottom = (p: number) => (p < 0.55 ? 0 : (p - 0.55) / 0.45);

const Chip = ({text, solid}: {text: string; solid?: boolean}) => (
  <View style={[styles.chip, solid && styles.chipSolid]}>
    <Text style={[styles.chipText, solid && styles.chipTextSolid]}>{text}</Text>
  </View>
);

const GameCard = ({
  g,
  now,
  onPress,
  onFocus,
}: {
  g: Game;
  now: boolean;
  onPress: () => void;
  onFocus?: () => void;
}) => {
  const teams = g.teams ?? [];
  const final = g.final;
  const scored =
    final &&
    teams.length === 2 &&
    teams.every((t) => typeof final[t] === 'number');
  return (
    <FocusButton
      onFocusChange={(f) => f && onFocus?.()}
      label={g.title}
      card
      onPress={onPress}
      outerStyle={styles.railOuter}
      style={[styles.game, now && styles.nowShowing]}>
      <View style={[StyleSheet.absoluteFill, styles.split, styles.teamTint]}>
        {teams.map((t) => (
          <View key={t} style={[styles.flex, {backgroundColor: team(t).bg}]} />
        ))}
      </View>
      {g.poster && (
        <Image
          source={{uri: g.poster}}
          style={[StyleSheet.absoluteFill, styles.posterImg]}
        />
      )}
      <Fade down alpha={(p) => (now ? 0.35 : 0.45) + (now ? 0.53 : 0.45) * p} />
      <View style={styles.circle} />
      {now && (
        <View style={styles.nowPill}>
          <Text style={styles.nowPillText}>▶ NOW SHOWING</Text>
        </View>
      )}
      <View style={styles.gameInfo}>
        <Text style={styles.gameTitle} numberOfLines={1}>
          {splitTitle(g.title)[0]}
        </Text>
        {scored && (
          <View style={styles.scoreRow}>
            {teams.map((t, i) => (
              <View
                key={t}
                style={[styles.score, {backgroundColor: team(t).bg}]}>
                <Text style={[styles.scoreText, {color: team(t).ink}]}>
                  {i === 0
                    ? `${t.toUpperCase()} ${final[t]}`
                    : `${final[t]} ${t.toUpperCase()}`}
                </Text>
              </View>
            ))}
            <Text style={styles.final}>FINAL</Text>
          </View>
        )}
      </View>
    </FocusButton>
  );
};

export const Home = ({
  manifest,
  error,
  party,
  games,
  gameUrl,
  onAirId,
  onGame,
  onHighlights,
  onParty,
  onPartyEnd,
  onSelect,
}: Props) => {
  const current = games.find((g) => g.manifestUrl === gameUrl);
  const tracks = manifest?.tracks ?? [];
  const onAir = tracks.find((t) => t.id === onAirId) ?? tracks[0];
  const scroll = useRef<ScrollView>(null);
  const gridY = useRef(0);
  const [focusGrid, setFocusGrid] = useState(false);
  const [focusTop, setFocusTop] = useState(true); // Watch button holds focus at launch
  // Vega's focus engine won't move focus to views below the visible area, so the grid and the hero are two
  // "pages": focusing the ▼ / ▲ links scrolls the other page into view and hands focus to its main item.
  const toGrid = () => {
    scroll.current?.scrollTo({y: gridY.current});
    setFocusTop(false);
    setFocusGrid(true);
  };
  const scrollTop = () => scroll.current?.scrollTo({y: 0});
  const scrollGrid = () => scroll.current?.scrollTo({y: gridY.current});
  const toTop = () => {
    scroll.current?.scrollTo({y: 0});
    setFocusTop(true);
  };
  const [joinOpen, setJoinOpen] = useState(false);

  const openParty = () => {
    onParty();
    setJoinOpen(true);
  };

  if (joinOpen && party && onAir) {
    return (
      <PartyJoin
        code={party.code}
        members={party.members}
        heading={vs(current)}
        onStart={() => onSelect(onAir)}
        onSolo={() => {
          onPartyEnd();
          onSelect(onAir);
        }}
        onBack={() => setJoinOpen(false)}
      />
    );
  }

  const langs = new Set(tracks.map((t) => t.lang)).size;
  const partyLabel = party ? `Watch party: ${party.code}` : 'Watch party';

  return (
    <ScrollView ref={scroll} style={styles.root}>
      {/* 2a hero + games rail */}
      <View style={styles.hero}>
        {current?.poster && (
          <Image source={{uri: current.poster}} style={styles.heroImg} />
        )}
        <View style={styles.heroImg}>
          <Fade alpha={heroSide} />
          <Fade down alpha={heroBottom} />
        </View>
        <View style={styles.header}>
          <Mark size={s(56)} />
          <Wordmark size={s(30)} />
        </View>

        <View style={styles.heroBlock}>
          <View style={styles.nowRow}>
            <View style={styles.dot} />
            <Text style={[eyebrow, styles.accent]}>
              NOW SHOWING · {vs(current)}
            </Text>
          </View>
          <Text style={styles.display}>Pick who calls the game.</Text>
          <Text style={styles.heroBody}>
            {tracks.length
              ? `${NUM[tracks.length] ?? tracks.length} AI commentators. `
              : ''}
            Ask “why?” out loud from your phone and get answers checked against
            the real play log.
          </Text>
          {error ? (
            <Text style={styles.heroBody}>
              Could not load the game: {error}
            </Text>
          ) : !onAir ? (
            <Text style={styles.heroBody}>Loading…</Text>
          ) : (
            <View style={styles.heroButtons}>
              <FocusButton
                label={`Watch with ${shortName(onAir)}`}
                primary
                hasTVPreferredFocus={focusTop}
                // Vega re-grabs hasTVPreferredFocus on every re-render while it's true: release it once held
                onFocusChange={(f) => {
                  if (f) {
                    scrollTop();
                    setFocusTop(false);
                    setFocusGrid(false);
                  }
                }}
                onPress={() => onSelect(onAir)}
                outerStyle={styles.btnOuter}
                style={[styles.btn, styles.btnPrimary]}>
                <View style={styles.btnRow}>
                  <View style={styles.play} />
                  <Text style={[styles.btnText, styles.btnTextPrimary]}>
                    Watch with {shortName(onAir)}
                  </Text>
                </View>
              </FocusButton>
              <FocusButton
                label="Change commentator"
                onPress={toGrid}
                onFocusChange={(f) => f && scrollTop()}
                outerStyle={styles.btnOuter}
                style={[styles.btn, styles.btnGlass]}>
                <Text style={styles.btnText}>Change commentator</Text>
              </FocusButton>
              <FocusButton
                label={partyLabel}
                onPress={openParty}
                onFocusChange={(f) => f && scrollTop()}
                outerStyle={styles.btnOuter}
                style={[styles.btn, styles.btnGlass]}>
                <Text style={styles.btnText}>Watch party</Text>
              </FocusButton>
            </View>
          )}
        </View>

        <View style={styles.rail}>
          <Text style={[eyebrow, styles.railHead]}>GAMES</Text>
          {/* ponytail: plain row, 3 cards fit; a horizontal ScrollView trapped D-pad focus on the VVD */}
          <View style={styles.railRow}>
            {games.map((g) => (
              <GameCard
                key={g.clipId}
                g={g}
                now={g.manifestUrl === gameUrl}
                onPress={() => onGame(g.manifestUrl)}
                onFocus={scrollTop}
              />
            ))}
          </View>
        </View>
        <View style={styles.downHint}>
          <Text style={styles.linkText}>▼ Commentators</Text>
        </View>
      </View>

      {/* 2b commentators grid */}
      {manifest && (
        <View
          style={styles.section}
          onLayout={(e) => (gridY.current = e.nativeEvent.layout.y)}>
          <FocusButton
            label="Games above"
            onPress={toTop}
            onFocusChange={(f) => f && scrollGrid()}
            outerStyle={styles.upLink}
            style={styles.linkBox}>
            <Text style={styles.linkText}>▲ Games</Text>
          </FocusButton>
          <View style={styles.gridHead}>
            <Text style={styles.h2}>Choose your commentator</Text>
            <Text style={styles.hint}>
              Switch any time during the game · {tracks.length} commentators,{' '}
              {langs} {langs === 1 ? 'language' : 'languages'}
            </Text>
          </View>
          <View style={styles.grid}>
            {tracks.map((tr) => {
              const booth = tr.kind === 'booth';
              const live = tr === onAir;
              return (
                <FocusButton
                  key={tr.id}
                  label={trackName(tr)}
                  card
                  onPress={() => onSelect(tr)}
                  hasTVPreferredFocus={focusGrid && live}
                  onFocusChange={(f) => {
                    if (f) {
                      scrollGrid();
                      setFocusGrid(false);
                    }
                  }}
                  outerStyle={styles.gridOuter}
                  style={[
                    styles.card,
                    booth && styles.cardWide,
                    live && styles.onAirCard,
                  ]}>
                  <View style={styles.cardRow}>
                    <PersonaIcon persona={personaOf(tr.id)} size={s(96)} />
                    <View style={styles.cardText}>
                      <Text style={styles.cardName} numberOfLines={1}>
                        {shortName(tr)}
                      </Text>
                      <Text style={styles.tagline} numberOfLines={2}>
                        {TAGLINES[tr.id] ?? trackTagline(tr)}
                      </Text>
                      <View style={styles.chips}>
                        {booth && <Chip solid text="PLAY-BY-PLAY" />}
                        {booth && <Chip solid text="ANALYST" />}
                        <Chip
                          text={`${LANG[tr.lang] ?? tr.lang}${
                            booth ? ' · 2 VOICES' : ''
                          }`}
                        />
                      </View>
                    </View>
                  </View>
                  {live && (
                    <View style={styles.onAirPill}>
                      <Text style={styles.nowPillText}>✓ ON AIR</Text>
                    </View>
                  )}
                </FocusButton>
              );
            })}
          </View>

          {/* More ways to watch */}
          <Text style={[eyebrow, styles.moreHead]}>MORE WAYS TO WATCH</Text>
          <View style={styles.grid}>
            {manifest.highlights && (
              <FocusButton
                label="Highlights"
                card
                onPress={onHighlights}
                outerStyle={styles.gridOuter}
                style={[styles.card, styles.cardWide, styles.more]}>
                <View style={styles.moreRow}>
                  <View style={styles.thumbs}>
                    {current?.poster && (
                      <Image
                        source={{uri: current.poster}}
                        style={styles.thumb}
                      />
                    )}
                    {(current?.teams ?? []).map((t) => (
                      <View
                        key={t}
                        style={[styles.thumb, {backgroundColor: team(t).bg}]}
                      />
                    ))}
                  </View>
                  <View style={styles.cardText}>
                    <Text style={styles.cardName}>Highlights</Text>
                    <Text style={styles.moreBody}>
                      {Math.round(manifest.highlights.duration)} s · every
                      verified basket, called by your commentator.
                    </Text>
                  </View>
                </View>
              </FocusButton>
            )}
            <FocusButton
              label={partyLabel}
              card
              onPress={openParty}
              outerStyle={styles.gridOuter}
              style={[styles.card, styles.cardWide, styles.more]}>
              <View style={styles.moreRow}>
                <View style={styles.phones}>
                  <View style={styles.phone} />
                  <View style={[styles.phone, styles.phoneAccent]} />
                </View>
                <View style={styles.cardText}>
                  <Text style={styles.cardName}>Watch party</Text>
                  <Text style={styles.moreBody}>
                    Everyone joins from their phone and calls the next basket.
                  </Text>
                </View>
              </View>
            </FocusButton>
          </View>
        </View>
      )}
      {current?.attribution && (
        <Text style={styles.footer}>{current.attribution}</Text>
      )}
    </ScrollView>
  );
};

// FocusButton draws its ring 11 px (8 border + 3 gap) outside the box, so rows start 11 px left of the
// safe edge and margins are the design gap minus 22.
const RING = 11;
const styles = StyleSheet.create({
  root: {flex: 1, backgroundColor: C.bg},
  hero: {height: s(1080)},
  heroImg: {
    position: 'absolute',
    right: 0,
    top: 0,
    width: s(1320),
    height: s(742),
  },
  header: {
    position: 'absolute',
    left: SAFE.x,
    top: SAFE.y,
    height: s(64),
    flexDirection: 'row',
    alignItems: 'center',
    gap: s(16),
  },
  heroBlock: {
    position: 'absolute',
    left: SAFE.x,
    top: s(196),
    width: s(1400),
    gap: s(24),
  },
  nowRow: {flexDirection: 'row', alignItems: 'center', gap: s(12)},
  dot: {
    width: s(12),
    height: s(12),
    borderRadius: s(6),
    backgroundColor: C.accent,
  },
  accent: {color: C.accent},
  display: {...T.display, color: C.text, maxWidth: s(900)},
  heroBody: {...T.bodyL, color: C.textSoft, maxWidth: s(900)},
  heroButtons: {
    flexDirection: 'row',
    marginTop: s(16 - RING),
    marginLeft: s(-RING),
  },
  btnOuter: {marginRight: s(24 - 2 * RING), marginBottom: 0},
  btn: {height: s(80), borderRadius: s(14), paddingHorizontal: s(32)},
  btnPrimary: {paddingHorizontal: s(36)},
  btnGlass: {backgroundColor: 'rgba(17,25,34,0.92)'},
  btnRow: {flexDirection: 'row', alignItems: 'center', gap: s(16)},
  play: {
    width: 0,
    height: 0,
    borderLeftWidth: s(20),
    borderTopWidth: s(13),
    borderBottomWidth: s(13),
    borderLeftColor: C.accentInk,
    borderTopColor: 'transparent',
    borderBottomColor: 'transparent',
  },
  btnText: {color: C.text, fontSize: s(28), fontWeight: '700'},
  btnTextPrimary: {color: C.accentInk, fontWeight: '800'},
  rail: {
    position: 'absolute',
    left: SAFE.x - s(RING),
    right: 0,
    top: s(690),
    gap: s(20 - RING),
  },
  railHead: {marginLeft: s(RING)},
  railRow: {flexDirection: 'row'},
  railOuter: {marginRight: s(32 - 2 * RING), marginBottom: 0},
  game: {
    width: s(540),
    height: s(248),
    borderRadius: s(20),
    overflow: 'hidden',
    padding: 0,
    paddingHorizontal: 0,
    borderWidth: 0,
  },
  nowShowing: {borderWidth: s(3), borderColor: C.accent},
  flex: {flex: 1},
  col: {flexDirection: 'column'},
  split: {flexDirection: 'row'},
  teamTint: {opacity: 0.6},
  posterImg: {width: '100%', height: '100%', opacity: 0.55},
  circle: {
    position: 'absolute',
    left: s(270 - 110),
    top: s(-40),
    width: s(220),
    height: s(220),
    borderRadius: s(110),
    borderWidth: s(3),
    borderColor: 'rgba(255,255,255,0.22)',
  },
  nowPill: {
    position: 'absolute',
    left: s(20),
    top: s(20),
    height: s(40),
    paddingHorizontal: s(14),
    borderRadius: 999,
    backgroundColor: C.accent,
    justifyContent: 'center',
  },
  nowPillText: {color: C.accentInk, fontSize: s(24), fontWeight: '800'},
  gameInfo: {
    position: 'absolute',
    left: s(24),
    right: s(24),
    bottom: s(20),
    gap: s(12),
  },
  gameTitle: {color: C.text, fontSize: s(30), fontWeight: '800'},
  scoreRow: {flexDirection: 'row', alignItems: 'center', gap: s(8)},
  score: {
    height: s(44),
    paddingHorizontal: s(14),
    borderRadius: s(10),
    justifyContent: 'center',
  },
  scoreText: {
    fontSize: s(24),
    fontWeight: '800',
    fontVariant: ['tabular-nums'],
  },
  final: {
    color: C.textSoft,
    fontSize: s(24),
    fontWeight: '700',
    marginLeft: s(8),
  },
  downHint: {
    position: 'absolute',
    left: SAFE.x - s(11),
    right: SAFE.x - s(11),
    bottom: s(-6),
  },
  upLink: {alignSelf: 'flex-start', marginLeft: SAFE.x - s(11)},
  linkBox: {
    minHeight: s(56),
    paddingHorizontal: s(20),
    backgroundColor: C.panel,
  },
  linkText: {color: C.muted, fontSize: s(24), fontWeight: '700'},
  section: {paddingTop: SAFE.y, paddingBottom: s(40)},
  gridHead: {
    marginHorizontal: SAFE.x,
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    marginBottom: s(28 - RING),
  },
  h2: {...T.h2, color: C.text},
  hint: {color: C.muted, fontSize: s(24)},
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginLeft: SAFE.x - s(RING),
    width: s(4 * (414 + 24) + 8),
  },
  gridOuter: {marginRight: s(24 - 2 * RING), marginBottom: s(24 - 2 * RING)},
  card: {
    width: s(414),
    height: s(226),
    padding: s(28),
    paddingHorizontal: s(28),
    borderRadius: s(20),
    borderWidth: 1,
    borderColor: C.line,
    backgroundColor: C.panel,
    justifyContent: 'flex-start',
  },
  cardWide: {width: s(414 * 2 + 24)},
  onAirCard: {borderWidth: s(3), borderColor: C.accent},
  cardRow: {flexDirection: 'row', gap: s(24), flex: 1},
  cardText: {flex: 1, gap: s(10)},
  cardName: {color: C.text, fontSize: s(32), fontWeight: '800'},
  tagline: {color: C.textSoft, fontSize: s(24), lineHeight: s(32)},
  chips: {flexDirection: 'row', gap: s(8), marginTop: 'auto'},
  chip: {
    height: s(40),
    paddingHorizontal: s(12),
    borderRadius: 999,
    borderWidth: 1,
    borderColor: C.lineStrong,
    justifyContent: 'center',
  },
  chipSolid: {backgroundColor: C.panel2},
  chipText: {color: C.muted, fontSize: s(24), fontWeight: '700'},
  chipTextSolid: {color: C.text, fontWeight: '800'},
  onAirPill: {
    position: 'absolute',
    right: s(20),
    top: s(20),
    height: s(40),
    paddingHorizontal: s(12),
    borderRadius: 999,
    backgroundColor: C.accent,
    justifyContent: 'center',
  },
  moreHead: {
    marginLeft: SAFE.x,
    marginTop: s(62 - RING - 2),
    marginBottom: s(44 - 30 - RING),
  },
  more: {height: s(200), justifyContent: 'center'},
  moreRow: {flexDirection: 'row', alignItems: 'center', gap: s(28)},
  moreBody: {color: C.textSoft, fontSize: s(24), lineHeight: s(34)},
  thumbs: {flexDirection: 'row', gap: s(8)},
  thumb: {width: s(120), height: s(144), borderRadius: s(12)},
  phones: {
    width: s(144),
    height: s(144),
    borderRadius: s(20),
    backgroundColor: C.panel2,
    borderWidth: 1,
    borderColor: C.lineStrong,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: s(10),
  },
  phone: {
    width: s(36),
    height: s(64),
    borderRadius: s(10),
    borderWidth: s(4),
    borderColor: C.text,
  },
  phoneAccent: {borderColor: C.accent},
  footer: {
    marginHorizontal: SAFE.x,
    marginBottom: SAFE.y,
    color: C.muted,
    fontSize: s(24),
  },
});
