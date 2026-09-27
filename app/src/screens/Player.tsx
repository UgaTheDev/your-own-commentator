import React, {useEffect, useRef, useState} from 'react';
import {BackHandler, StyleSheet, Text, View} from 'react-native';
import {
  AudioPlayer,
  KeplerVideoSurfaceView,
  VideoPlayer,
} from '@amazon-devices/react-native-w3cmedia';
import {FocusButton} from '../components/FocusButton';
import {AUTOPILOT} from '../config';
import {
  Manifest,
  Question,
  Track,
  activeAt,
  answerFor,
  trackName,
  whyAt,
} from '../manifest';

const TEACHABLE = new Set(['foul', 'travel', 'turnover', 'made_3', 'ft_made']);
const CARD_SECS = 6;
const CAPTION_SECS = 6;
const TOAST_MS = 2500;
const ROLE = {pbp: 'PLAY-BY-PLAY', analyst: 'ANALYST'};
// console.warn: info level is suppressed for the first seconds after launch
const log = (msg: string) => console.warn(`YOC: ${msg}`);
const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

type Media = VideoPlayer | AudioPlayer;
const once = (v: Media, type: string, fn: () => void) => {
  const h = () => {
    v.removeEventListener(type, h);
    fn();
  };
  v.addEventListener(type, h);
};

// What covers the game while the video is paused.
type Overlay =
  | {kind: 'why'; eventId: string; questions: Question[]; answer?: string}
  | {kind: 'recap'; text: string};

interface Props {
  manifest: Manifest;
  initial: Track;
  onBack: () => void;
}

export const Player = ({manifest, initial, onBack}: Props) => {
  const player = useRef<VideoPlayer | null>(null);
  const audio = useRef<AudioPlayer | null>(null);
  const speakId = useRef(0);
  const switchId = useRef(0);
  const switchingNow = useRef(false);
  const [track, setTrack] = useState(initial);
  const [t, setT] = useState(0);
  const [switching, setSwitching] = useState<string | null>(null);
  const [overlay, setOverlayState] = useState<Overlay | null>(null);
  const overlayRef = useRef<Overlay | null>(null);
  const setOverlay = (o: Overlay | null) => {
    overlayRef.current = o;
    setOverlayState(o);
  };
  const [toast, setToast] = useState<string | null>(null);
  const surface = useRef<(h: string) => void>(() => {});
  const surfaceReady = useRef(
    new Promise<string>((r) => {
      surface.current = r;
    }),
  );

  useEffect(() => {
    const v = new VideoPlayer();
    const a = new AudioPlayer();
    let poll = 0;
    let alive = true;
    (async () => {
      await v.initialize();
      v.setSurfaceHandle(await surfaceReady.current);
      if (!alive) {
        return;
      }
      player.current = v;
      v.addEventListener('error', () =>
        log(`error ${JSON.stringify(v.error)}`),
      );
      v.src = initial.src;
      v.play();
      log(`play ${initial.id}`);
      // ponytail: poll instead of timeupdate, which may not fire reliably
      poll = setInterval(() => {
        if (!switchingNow.current) {
          setT(v.currentTime);
        }
      }, 250);
      // Second player for Why answers and recaps (spike S2: plays over a paused video).
      await a.initialize();
      if (!alive) {
        return;
      }
      a.addEventListener('error', () =>
        log(`audio error ${JSON.stringify(a.error)}`),
      );
      audio.current = a;
      log('audio player ready');
    })().catch((e) => log(`FATAL ${e}`));
    return () => {
      alive = false;
      clearInterval(poll);
      player.current = null;
      audio.current = null;
      v.pause();
      v.deinitialize().catch(() => {});
      a.pause();
      a.deinitialize().catch(() => {});
    };
  }, [initial]);

  // Close the Why/recap card, stop its audio and resume the game.
  const closeOverlay = (how: string) => {
    if (!overlayRef.current) {
      return;
    }
    speakId.current++;
    audio.current?.pause();
    setOverlay(null);
    player.current?.play();
    log(
      `overlay closed (${how}), resume t=${player.current?.currentTime.toFixed(
        2,
      )}`,
    );
  };

  // Play one clip in the second player; close the overlay when it ends.
  const speak = (url: string, what: string) => {
    const a = audio.current;
    if (!a) {
      log(`${what}: no audio player, text only`);
      return;
    }
    const id = ++speakId.current;
    const started = Date.now();
    once(a, 'playing', () =>
      log(`${what} audio playing after ${Date.now() - started}ms`),
    );
    once(a, 'ended', () => {
      if (id === speakId.current) {
        closeOverlay(`${what} ended after ${Date.now() - started}ms`);
      }
    });
    a.src = url;
    a.play();
  };

  const showToast = (text: string) => {
    setToast(text);
    log(`toast "${text}"`);
    setTimeout(() => setToast((cur) => (cur === text ? null : cur)), TOAST_MS);
  };

  const why = () => {
    const v = player.current;
    if (!v || overlayRef.current) {
      return;
    }
    const now = v.currentTime;
    const hit = whyAt(manifest, now);
    if (!hit) {
      showToast('Nothing to explain yet');
      return;
    }
    v.pause();
    setOverlay({kind: 'why', eventId: hit.event.id, questions: hit.questions});
    log(
      `why ${hit.event.id} at t=${now.toFixed(2)} questions=${
        hit.questions.length
      }`,
    );
  };

  const pick = (q: Question) => {
    const o = overlayRef.current;
    const ans = answerFor(q, track.id);
    if (o?.kind !== 'why' || !ans) {
      return;
    }
    setOverlay({...o, answer: ans.text});
    log(`why answer "${q.q}" -> ${ans.audioUrl}`);
    speak(ans.audioUrl, 'why');
  };

  const catchUp = () => {
    const v = player.current;
    if (!v || overlayRef.current) {
      return;
    }
    const now = v.currentTime;
    const r = activeAt(manifest.recaps ?? [], now);
    if (!r) {
      showToast('Nothing to catch up on yet');
      return;
    }
    // ponytail: pause rather than duck; volume ducking needs a VVD check first
    v.pause();
    setOverlay({kind: 'recap', text: r.text});
    log(`recap t=${r.t} at t=${now.toFixed(2)} -> ${r.src}`);
    speak(r.src, 'recap');
  };

  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', () => {
      log('back');
      if (overlayRef.current) {
        closeOverlay('back');
      } else {
        onBack();
      }
      return true;
    });
    return () => sub.remove();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onBack]);

  // Option 2c from spike S2: new src, then seek to the saved time.
  const switchTo = (next: Track) => {
    const v = player.current;
    if (!v || next.id === track.id) {
      return;
    }
    const id = ++switchId.current;
    const saved = v.currentTime;
    const started = Date.now();
    const finish = (how: string) => {
      if (id !== switchId.current || !switchingNow.current) {
        return;
      }
      switchingNow.current = false;
      setSwitching(null);
      log(
        `${how} ${next.id} t=${v.currentTime.toFixed(2)} saved=${saved.toFixed(
          2,
        )} after ${Date.now() - started}ms`,
      );
    };
    switchingNow.current = true;
    setTrack(next);
    setSwitching(trackName(next));
    log(`switch to ${next.id} at t=${saved.toFixed(2)}`);
    once(v, 'loadedmetadata', () => {
      if (id !== switchId.current) {
        return;
      }
      once(v, 'seeked', () => finish('seeked'));
      v.currentTime = saved;
      v.play();
    });
    v.src = next.src;
    // ponytail: drop the overlay if seeked never arrives
    setTimeout(() => finish('switch timeout'), 10000);
  };

  // Autopilot calls through a ref so it always sees the latest render's state.
  const api = useRef({why, pick, catchUp, switchTo});
  api.current = {why, pick, catchUp, switchTo};
  useEffect(() => {
    if (!AUTOPILOT) {
      return;
    }
    let alive = true;
    const seek = (s: number) => {
      const v = player.current;
      if (v) {
        v.currentTime = s;
        log(`auto seek ${s}`);
      }
    };
    const booth = manifest.tracks.find((tr) => tr.kind === 'booth');
    const steps: [number, () => void][] = [
      [15000, () => seek(32)],
      [8000, () => api.current.why()], // e2 at 34.5; seeks land ~3 s late
      [
        2000,
        () => {
          const o = overlayRef.current;
          if (o?.kind === 'why') {
            api.current.pick(o.questions[0]);
          }
        },
      ],
      [10000, () => seek(50)],
      [2000, () => api.current.why()], // nothing within 10 s
      [3000, () => seek(121)],
      [3000, () => api.current.catchUp()], // recap t=120
      [12000, () => booth && api.current.switchTo(booth)],
      [16000, () => log('auto done')],
    ];
    (async () => {
      for (const [ms, fn] of steps) {
        await sleep(ms);
        if (!alive) {
          return;
        }
        fn();
      }
    })();
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const score = activeAt(manifest.state, t)?.score;
  const ev = activeAt(manifest.events, t);
  // ponytail: only the latest event can show a card; a later non-teachable event hides it early
  const card =
    track.persona === 'rookie' &&
    ev?.ruleCardId &&
    t - ev.t < CARD_SECS &&
    (TEACHABLE.has(ev.type) || ev.ruleCardId === 'and_one')
      ? manifest.ruleCards[ev.ruleCardId]
      : undefined;

  const cue =
    track.kind === 'booth' ? activeAt(manifest.cues[track.id] ?? [], t) : null;
  const caption = cue && t - cue.t < CAPTION_SECS ? cue : null;

  const scoreText = score ? `pink ${score.pink} - ${score.blue} blue` : '';
  useEffect(() => {
    log(`score ${scoreText || 'none'} t=${t.toFixed(2)}`);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scoreText]);
  useEffect(() => {
    log(
      `card ${card ? `${ev?.id} ${card.title}` : 'hidden'} t=${t.toFixed(2)}`,
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [card]);
  useEffect(() => {
    log(
      `caption ${
        caption
          ? `${caption.role ? ROLE[caption.role] : '-'} "${caption.text}"`
          : 'hidden'
      } t=${t.toFixed(2)}`,
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caption]);

  return (
    <View style={styles.root}>
      <KeplerVideoSurfaceView
        style={styles.video}
        onSurfaceViewCreated={(h: string) => surface.current(h)}
        onSurfaceViewDestroyed={(h: string) =>
          player.current?.clearSurfaceHandle(h)
        }
      />
      {score && (
        <View style={styles.scoreBug}>
          <Text style={[styles.team, styles.pink]}>PINK {score.pink}</Text>
          <Text style={[styles.team, styles.blue]}>BLUE {score.blue}</Text>
        </View>
      )}
      {card && !overlay && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>{card.title}</Text>
          <Text style={styles.cardBody}>{card.body}</Text>
        </View>
      )}
      {caption && !overlay && (
        <View style={styles.caption}>
          {caption.role && (
            <Text style={styles.role}>{ROLE[caption.role]}</Text>
          )}
          <Text style={styles.captionText}>{caption.text}</Text>
        </View>
      )}
      {overlay && (
        <View style={styles.panel}>
          <Text style={styles.cardTitle}>
            {overlay.kind === 'why' ? 'Why?' : 'Catch me up'}
          </Text>
          {overlay.kind === 'why' && !overlay.answer ? (
            overlay.questions.map((q, i) => (
              <FocusButton
                key={q.q}
                label={q.q}
                onPress={() => pick(q)}
                hasTVPreferredFocus={i === 0}
              />
            ))
          ) : (
            <>
              <Text style={styles.cardBody}>
                {overlay.kind === 'why' ? overlay.answer : overlay.text}
              </Text>
              <FocusButton
                label="Back to game"
                onPress={() => closeOverlay('button')}
                hasTVPreferredFocus
              />
            </>
          )}
        </View>
      )}
      {toast && (
        <View style={styles.switching}>
          <Text style={styles.switchingText}>{toast}</Text>
        </View>
      )}
      {switching && (
        <View style={styles.switching}>
          <Text style={styles.switchingText}>Switching to {switching}…</Text>
        </View>
      )}
      {/* next (Sprint 2): replay button for manifest.replays, minimap from manifest.minimap, fantasy panel */}
      <View style={styles.bar}>
        <FocusButton label="Why?" onPress={why} />
        <FocusButton label="Catch me up" onPress={catchUp} />
        {manifest.tracks.map((tr) => (
          <FocusButton
            key={tr.id}
            label={trackName(tr)}
            selected={tr.id === track.id}
            onPress={() => switchTo(tr)}
            hasTVPreferredFocus={tr.id === initial.id}
          />
        ))}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  root: {flex: 1, backgroundColor: '#000'},
  video: {position: 'absolute', top: 0, left: 0, right: 0, bottom: 0},
  scoreBug: {
    position: 'absolute',
    top: '5%',
    left: '5%',
    flexDirection: 'row',
    backgroundColor: 'rgba(0,0,0,0.8)',
    borderRadius: 12,
    overflow: 'hidden',
  },
  team: {
    color: '#FFFFFF',
    fontSize: 40,
    fontWeight: '800',
    paddingVertical: 10,
    paddingHorizontal: 24,
  },
  pink: {backgroundColor: '#d6247a'},
  blue: {backgroundColor: '#1f5fd6'},
  card: {
    position: 'absolute',
    top: '5%',
    right: '5%',
    width: '38%',
    padding: 28,
    borderRadius: 16,
    backgroundColor: 'rgba(10,14,26,0.9)',
    borderLeftWidth: 8,
    borderLeftColor: '#FFD400',
  },
  panel: {
    position: 'absolute',
    top: '18%',
    left: '5%',
    width: '55%',
    padding: 32,
    borderRadius: 16,
    backgroundColor: 'rgba(10,14,26,0.94)',
    borderLeftWidth: 8,
    borderLeftColor: '#FFD400',
    alignItems: 'flex-start',
  },
  cardTitle: {color: '#FFD400', fontSize: 44, fontWeight: '700'},
  cardBody: {
    color: '#FFFFFF',
    fontSize: 30,
    lineHeight: 40,
    marginTop: 12,
    marginBottom: 20,
  },
  caption: {
    position: 'absolute',
    bottom: '20%',
    left: '10%',
    right: '10%',
    padding: 20,
    borderRadius: 12,
    backgroundColor: 'rgba(0,0,0,0.8)',
  },
  role: {color: '#FFD400', fontSize: 24, fontWeight: '800', letterSpacing: 2},
  captionText: {color: '#FFFFFF', fontSize: 34, lineHeight: 44, marginTop: 6},
  switching: {
    position: 'absolute',
    top: '42%',
    alignSelf: 'center',
    paddingVertical: 24,
    paddingHorizontal: 48,
    borderRadius: 16,
    backgroundColor: 'rgba(0,0,0,0.85)',
  },
  switchingText: {color: '#FFFFFF', fontSize: 48, fontWeight: '700'},
  bar: {
    position: 'absolute',
    bottom: '4%',
    left: '5%',
    right: '5%',
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
});
