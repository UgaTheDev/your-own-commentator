import React, {useEffect, useState} from 'react';
import {AUTOPILOT, MANIFEST_URL, WS_ECHO_URL, WS_SPIKE} from './config';
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
        if (AUTOPILOT) {
          setTrack(m.tracks[0]);
        }
      })
      .catch((e) => {
        console.warn(`YOC: manifest error ${e}`);
        setError(String(e));
      });
  }, []);

  // Spike: does RN WebSocket work on Vega? Waits past the ~12 s of suppressed launch logs.
  useEffect(() => {
    if (!WS_SPIKE) {
      return;
    }
    const timer = setTimeout(() => {
      const started = Date.now();
      const ws = new WebSocket(WS_ECHO_URL);
      ws.onopen = () => {
        console.warn(`YOC: ws open after ${Date.now() - started}ms`);
        ws.send('yoc-ping');
      };
      ws.onmessage = (e) => {
        console.warn(
          `YOC: ws WORKS echo="${e.data}" after ${Date.now() - started}ms`,
        );
        ws.close();
      };
      ws.onerror = (e) =>
        console.warn(`YOC: ws FAILS error ${JSON.stringify(e)}`);
      ws.onclose = (e) => console.warn(`YOC: ws close code=${e.code}`);
    }, 14000);
    return () => clearTimeout(timer);
  }, []);

  return manifest && track ? (
    <Player manifest={manifest} initial={track} onBack={() => setTrack(null)} />
  ) : (
    <Home manifest={manifest} error={error} onSelect={setTrack} />
  );
};
