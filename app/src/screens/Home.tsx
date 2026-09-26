import React from 'react';
import {StyleSheet, Text, View} from 'react-native';
import {FocusButton} from '../components/FocusButton';
import {Manifest, Track, trackName} from '../manifest';

interface Props {
  manifest: Manifest | null;
  error: string | null;
  onSelect: (track: Track) => void;
}

export const Home = ({manifest, error, onSelect}: Props) => (
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
  list: {marginTop: 56, alignItems: 'flex-start'},
});
