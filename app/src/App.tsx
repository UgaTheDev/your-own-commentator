import React, {useEffect, useRef, useState} from 'react';
import {
  AUTOPILOT,
  FALLBACK_GAMES,
  GAMES_URL,
  MANIFEST_URL,
  PARTY_WS_URL,
  WS_ECHO_URL,
  WS_SPIKE,
} from './config';
import {
  Game,
  Manifest,
  Track,
  fetchGames,
  fetchManifest,
  trackName,
} from './manifest';
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

  // C8 game picker: the index when it's up, else the one demo manifest; retried each time Home shows.
  const [games, setGames] = useState<Game[]>(FALLBACK_GAMES);
  const [indexed, setIndexed] = useState(false);
  const [gameUrl, setGameUrl] = useState(MANIFEST_URL);
  const [reel, setReel] = useState(false);
  useEffect(() => {
    if (track || indexed) {
      return;
    }
    fetchGames(GAMES_URL)
      .then((g) => {
        log(`games ${g.map((x) => `${x.clipId}=${x.title}`).join('|')}`);
        setGames(g);
        setIndexed(true);
        if (!g.some((x) => x.manifestUrl === gameUrl)) {
          setGameUrl(g[0].manifestUrl);
        }
      })
      .catch((e) => log(`games index unavailable (${e}), fallback lake-region`));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [track, indexed]);

  const pickGame = (url: string) => {
    if (url === gameUrl) {
      return;
    }
    setParty(null); // a room settles predictions from one clip; the [party] effect stops the old one
    setManifest(null);
    setError(null);
    setGameUrl(url);
    log(`game ${url}`);
  };

  useEffect(() => {
    let current = true; // a slower fetch for a game picked earlier must not win
    fetchManifest(gameUrl)
      .then((m) => {
        if (!current) {
          return;
        }
        m.tracks.sort((a, b) => rank(a) - rank(b));
        console.warn(
          `YOC: manifest ${m.clipId} tracks=${m.tracks
            .map(trackName)
            .join('|')} events=${m.events.length} highlights=${
            m.highlights ? `${m.highlights.duration}s` : 'none'
          }`,
        );
        setManifest(m);
        if (AUTOPILOT) {
          setTrack(m.tracks[0]);
        }
      })
      .catch((e) => {
        if (current) {
          console.warn(`YOC: manifest error ${e}`);
          setError(String(e));
        }
      });
    return () => {
      current = false;
    };
  }, [gameUrl]);

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
      startHighlights={reel}
      onBack={() => {
        setReel(false);
        setTrack(null);
      }}
    />
  ) : (
    <Home
      manifest={manifest}
      error={error}
      party={partyView}
      games={games}
      gameUrl={gameUrl}
      onGame={pickGame}
      onHighlights={() => {
        if (manifest?.highlights) {
          setReel(true);
          setTrack(manifest.tracks[0]);
        }
      }}
      onParty={startParty}
      onSelect={setTrack}
    />
  );
};
