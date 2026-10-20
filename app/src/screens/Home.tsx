import React from 'react';
import {Image, StyleSheet, Text, View} from 'react-native';
import {FocusButton} from '../components/FocusButton';
import {Game, Manifest, Track, trackName, trackTagline} from '../manifest';
import {Member} from '../party';
import {C, eyebrow, s, team} from '../theme';

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
  onGame: (manifestUrl: string) => void;
  onHighlights: () => void;
  onParty: () => void;
  onSelect: (track: Track) => void;
}

// Card name without the bracketed language: the tag beside it says that.
const shortName = (tr: Track) => trackName(tr).replace(/\s*\(.*\)$/, '');
// "Hazen vs X (girls varsity)" -> ["Hazen vs X", "GIRLS VARSITY"]
const splitTitle = (t: string) => {
  const m = t.match(/^(.*?)\s*\((.*)\)$/);
  return m ? [m[1], m[2].toUpperCase()] : [t, ''];
};

const LANG: Record<string, string> = {en: 'EN', es: 'ES', hi: 'HI', zh: 'ZH'};

const Score = ({final, teams}: {final: Record<string, number>; teams: string[]}) => (
  <View style={styles.scoreRow}>
    {teams.map((t) => (
      <View key={t} style={[styles.chip, {backgroundColor: team(t).bg}]}>
        <Text style={[styles.chipText, {color: team(t).ink}]}>
          {t.toUpperCase()} {final[t] ?? 0}
        </Text>
      </View>
    ))}
  </View>
);

export const Home = ({
  manifest,
  error,
  party,
  games,
  gameUrl,
  onGame,
  onHighlights,
  onParty,
  onSelect,
}: Props) => {
  const current = games.find((g) => g.manifestUrl === gameUrl);
  return (
    <View style={styles.root}>
      <View style={styles.header}>
        <View>
          <Text style={eyebrow}>FIRE TV · FACT-CHECKED COMMENTARY</Text>
          <Text style={styles.title}>Your Own Commentator</Text>
          <Text style={styles.subtitle}>
            Same game, your call. Pick who talks you through it.
          </Text>
        </View>
        <View style={styles.status}>
          <View style={styles.dot} />
          <Text style={[eyebrow, styles.statusText]}>
            {games.length} GAMES · VERIFIED EVENTS ONLY
          </Text>
        </View>
      </View>

      <Text style={[eyebrow, styles.section]}>GAMES</Text>
      <View style={styles.row}>
        {games.map((g) => (
          <FocusButton
            key={g.clipId}
            label={g.title}
            selected={g.manifestUrl === gameUrl}
            onPress={() => onGame(g.manifestUrl)}
            style={styles.game}>
            {g.poster ? (
              <Image source={{uri: g.poster}} style={styles.poster} />
            ) : (
              <View style={styles.poster} />
            )}
            <View style={styles.gameInfo}>
              <Text
                style={[
                  eyebrow,
                  g.manifestUrl === gameUrl && styles.accentText,
                ]}>
                {g.manifestUrl === gameUrl ? '● ' : ''}
                {splitTitle(g.title)[1]}
              </Text>
              <Text style={styles.gameTitle} numberOfLines={1}>
                {splitTitle(g.title)[0]}
              </Text>
              {g.final && g.teams && <Score final={g.final} teams={g.teams} />}
            </View>
          </FocusButton>
        ))}
      </View>

      <Text style={[eyebrow, styles.section]}>
        {manifest
          ? `COMMENTATORS · ${manifest.tracks.length}${
              current ? ` · ${current.title.toUpperCase()}` : ''
            }`
          : 'COMMENTATORS'}
      </Text>
      {error ? (
        <Text style={styles.subtitle}>Could not load the game: {error}</Text>
      ) : !manifest ? (
        <Text style={styles.subtitle}>Loading…</Text>
      ) : (
        <View style={styles.row}>
          {manifest.tracks.map((tr, i) => (
            <FocusButton
              key={tr.id}
              label={trackName(tr)}
              onPress={() => onSelect(tr)}
              hasTVPreferredFocus={i === 0}
              style={styles.track}>
              <View style={styles.trackTop}>
                <Text style={styles.trackName} numberOfLines={1}>
                  {shortName(tr)}
                </Text>
                <Text style={styles.lang}>
                  {tr.kind === 'booth' ? '2 VOICES' : LANG[tr.lang] ?? tr.lang}
                </Text>
              </View>
              <Text style={styles.tagline} numberOfLines={1}>
                {trackTagline(tr)}
              </Text>
            </FocusButton>
          ))}
          {manifest.highlights && (
            <FocusButton
              label="Highlights"
              onPress={onHighlights}
              style={[styles.track, styles.accentCard]}>
              <Text style={[styles.trackName, styles.accentText]}>
                Highlights
              </Text>
              <Text style={styles.tagline}>
                {Math.round(manifest.highlights.duration)} s · every verified
                basket
              </Text>
            </FocusButton>
          )}
          <FocusButton
            label={party ? `Watch party: ${party.code}` : 'Watch party'}
            selected={!!party}
            onPress={onParty}
            style={styles.track}>
            <Text style={styles.trackName}>
              {party ? `Party ${party.code}` : 'Watch party'}
            </Text>
            <Text style={styles.tagline} numberOfLines={1}>
              {party
                ? party.members.length
                  ? party.members.map((m) => `${m.name} ${m.points}`).join(' · ')
                  : 'Connecting…'
                : 'Friends join with a code'}
            </Text>
          </FocusButton>
        </View>
      )}
      {current?.attribution && (
        <Text style={styles.footer}>{current.attribution}</Text>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: C.bg,
    paddingHorizontal: '4%',
    paddingTop: '3%',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  title: {color: C.text, fontSize: s(76), fontWeight: '800', marginTop: s(8)},
  subtitle: {color: C.muted, fontSize: s(30), marginTop: s(6)},
  status: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: C.line,
    borderRadius: 999,
    paddingVertical: s(10),
    paddingHorizontal: s(20),
    backgroundColor: C.panel,
  },
  dot: {
    width: s(12),
    height: s(12),
    borderRadius: s(6),
    backgroundColor: '#3ddc84',
    marginRight: s(12),
  },
  statusText: {color: C.text},
  section: {marginTop: s(22), marginBottom: s(12)},
  row: {flexDirection: 'row', flexWrap: 'wrap'},
  game: {
    width: s(520),
    padding: 0,
    borderRadius: s(18),
    overflow: 'hidden',
    backgroundColor: C.panel,
  },
  poster: {width: '100%', height: s(180), backgroundColor: C.panel2},
  gameInfo: {paddingVertical: s(14), paddingHorizontal: s(18)},
  gameTitle: {
    color: C.text,
    fontSize: s(30),
    fontWeight: '700',
    marginTop: s(4),
  },
  scoreRow: {flexDirection: 'row', marginTop: s(10)},
  chip: {
    borderRadius: s(8),
    paddingVertical: s(4),
    paddingHorizontal: s(12),
    marginRight: s(10),
  },
  chipText: {fontSize: s(20), fontWeight: '800', letterSpacing: s(1)},
  track: {
    width: s(322),
    borderRadius: s(16),
    paddingVertical: s(16),
    paddingHorizontal: s(22),
    backgroundColor: C.panel,
  },
  trackTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  trackName: {color: C.text, fontSize: s(30), fontWeight: '700', flexShrink: 1},
  lang: {
    color: C.muted,
    fontSize: s(18),
    fontWeight: '700',
    letterSpacing: s(2),
    borderWidth: 2,
    borderColor: C.line,
    borderRadius: s(6),
    paddingHorizontal: s(8),
    paddingVertical: s(2),
    marginLeft: s(10),
  },
  tagline: {color: C.muted, fontSize: s(22), marginTop: s(6)},
  accentCard: {backgroundColor: C.accentSoft},
  accentText: {color: C.accent},
  footer: {
    position: 'absolute',
    bottom: '3%',
    left: '4%',
    color: C.muted,
    fontSize: s(18),
  },
});
