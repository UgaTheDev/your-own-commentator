import React from 'react';
import {StyleSheet, Text, View} from 'react-native';
import {FocusButton} from '../components/FocusButton';
import {Manifest, Track, trackName} from '../manifest';
import {Member} from '../party';

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
  onParty: () => void;
  onSelect: (track: Track) => void;
}

export const Home = ({manifest, error, party, onParty, onSelect}: Props) => (
  <View style={styles.root}>
    <Text style={styles.title}>Your Own Commentator</Text>
    <Text style={styles.subtitle}>
      Same game, your call. Pick who talks you through it.
    </Text>
    {error ? (
      <Text style={styles.subtitle}>Could not load the game: {error}</Text>
    ) : !manifest ? (
      <Text style={styles.subtitle}>Loading…</Text>
    ) : (
      <View style={styles.list}>
        {manifest.tracks.map((tr, i) => (
          <FocusButton
            key={tr.id}
            label={trackName(tr)}
            onPress={() => onSelect(tr)}
            hasTVPreferredFocus={i === 0}
          />
        ))}
        <FocusButton
          label={party ? `Watch party: ${party.code}` : 'Watch party'}
          selected={!!party}
          onPress={onParty}
        />
        {party && (
          <Text style={[styles.subtitle, styles.party]}>
            Friends join with code {party.code}. In the room:{' '}
            {party.members.length
              ? party.members.map((m) => `${m.name} (${m.points})`).join(', ')
              : 'connecting…'}
          </Text>
        )}
      </View>
    )}
  </View>
);

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: '#0b0f1a',
    paddingHorizontal: '5%',
    paddingVertical: '5%',
  },
  title: {color: '#FFFFFF', fontSize: 72, fontWeight: '700'},
  subtitle: {color: '#C8CEDC', fontSize: 34, marginTop: 16},
  list: {marginTop: 56, flexDirection: 'row', flexWrap: 'wrap'},
  party: {width: '100%'},
});
