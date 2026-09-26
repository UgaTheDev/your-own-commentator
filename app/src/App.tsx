import React, {useEffect, useState} from 'react';
import {MANIFEST_URL} from './config';
import {Manifest, Track, fetchManifest, trackName} from './manifest';
import {Home} from './screens/Home';
import {Player} from './screens/Player';

const ORDER = ['rookie-en', 'kid-en', 'rookie-es'];
const rank = (tr: Track) => {
  const i = ORDER.indexOf(tr.id);
  return i < 0 ? ORDER.length : i;
};

export const App = () => {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [track, setTrack] = useState<Track | null>(null);

  useEffect(() => {
    fetchManifest(MANIFEST_URL)
      .then((m) => {
        m.tracks.sort((a, b) => rank(a) - rank(b));
        console.warn(
          `YOC: manifest ${m.clipId} tracks=${m.tracks
            .map(trackName)
            .join('|')} events=${m.events.length}`,
        );
        setManifest(m);
      })
      .catch((e) => {
        console.warn(`YOC: manifest error ${e}`);
        setError(String(e));
      });
  }, []);

  return manifest && track ? (
    <Player manifest={manifest} initial={track} onBack={() => setTrack(null)} />
  ) : (
    <Home manifest={manifest} error={error} onSelect={setTrack} />
  );
};
