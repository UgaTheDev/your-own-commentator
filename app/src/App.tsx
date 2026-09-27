import React, {useEffect, useRef, useState} from 'react';
import {
  AUTOPILOT,
  MANIFEST_URL,
  PARTY_WS_URL,
  WS_ECHO_URL,
  WS_SPIKE,
} from './config';
import {Manifest, Track, fetchManifest, trackName} from './manifest';
import {Member, Party, connectParty, gainers, newCode} from './party';
import {Home} from './screens/Home';
import {Player} from './screens/Player';

const ORDER = [
  'rookie-en',
  'kid-en',
  'booth-en',
  'fantasy-en',
  'rookie-es',
  'rookie-hi',
  'rookie-zh',
];
const TV_NAME = 'TV';
const BANNER_MS = 5000;
const log = (msg: string) => console.warn(`YOC: ${msg}`);
const rank = (tr: Track) => {
  const i = ORDER.indexOf(tr.id);
  return i < 0 ? ORDER.length : i;
};

export const App = () => {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [track, setTrack] = useState<Track | null>(null);
  // C6 watch party: one room code per app launch, joined from Home, kept across Player visits.
  const [partyCode] = useState(() => newCode());
  const [party, setParty] = useState<Party | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [banner, setBanner] = useState<string | null>(null);
  const membersRef = useRef<Member[]>([]);
  const resolved = useRef(false);

  const startParty = () => {
    if (party || !manifest) {
      return;
    }
    setParty(
      connectParty({
        url: manifest.party?.wsUrl ?? PARTY_WS_URL,
        code: partyCode,
        name: TV_NAME,
        trackId: manifest.tracks[0].id,
        clipId: manifest.clipId,
        onResolve: () => {
          resolved.current = true;
        },
        onState: (next) => {
          const won = gainers(membersRef.current, next).map((n) =>
            n === TV_NAME ? 'You' : n,
          );
          membersRef.current = next;
          setMembers(next);
          if (!resolved.current) {
            return;
          }
          resolved.current = false;
          const text = won.length
            ? `${won.join(' & ')} called it! +1`
            : 'Nobody called that one';
          log(`party banner "${text}"`);
          setBanner(text);
          setTimeout(() => setBanner((b) => (b === text ? null : b)), BANNER_MS);
        },
        log,
      }),
    );
  };
  useEffect(() => () => party?.stop(), [party]);
  const partyView = party && {
    code: partyCode,
    members,
    banner,
    send: party.send,
  };

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
    <Player
      manifest={manifest}
      initial={track}
      party={partyView}
      onBack={() => setTrack(null)}
    />
  ) : (
    <Home
      manifest={manifest}
      error={error}
      party={partyView}
      onParty={startParty}
      onSelect={setTrack}
    />
  );
};
