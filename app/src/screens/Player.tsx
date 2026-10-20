import React, {useEffect, useRef, useState} from 'react';
import {BackHandler, StyleSheet, Text, View} from 'react-native';
import {
  AudioPlayer,
  KeplerVideoSurfaceView,
  VideoPlayer,
} from '@amazon-devices/react-native-w3cmedia';
import {FocusButton} from '../components/FocusButton';
import {C, eyebrow, s, team} from '../theme';
import {AUTOPILOT, TALK_WS_URL} from '../config';
import {TalkAnswer, connectTalk} from '../talk';
import {PartyView} from './Home';
import {
  Manifest,
  Question,
  Track,
  activeAt,
  answerFor,
  replayAt,
  trackName,
  whyAt,
} from '../manifest';

const TEACHABLE = new Set(['foul', 'travel', 'turnover', 'made_3', 'ft_made']);
const CARD_SECS = 6;
const CAPTION_SECS = 6;
const TOAST_MS = 2500;
const ROLE = {pbp: 'PLAY-BY-PLAY', analyst: 'ANALYST'};
const COURT = {w: 28.65, h: 15.24}; // meters, C3 minimap units
const MAP_W = s(330);
const MAP_H = (MAP_W * COURT.h) / COURT.w;
// console.warn: info level is suppressed for the first seconds after launch
// @epoch ms lets scripts/demo rebuild the soundtrack of a screen recording from this log
const log = (msg: string) => console.warn(`YOC: @${Date.now()} ${msg}`);
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
  | {kind: 'recap'; text: string}
  | {kind: 'answer'; text: string} // C4 talk-back answer, shown as an ANALYST caption
  | {kind: 'predict'}; // C6: next basket, Pink or Blue (the game keeps playing)

interface Props {
  manifest: Manifest;
  initial: Track;
  party: PartyView | null;
  startHighlights?: boolean; // opened from Home's Highlights: play the reel, then go back
  onBack: () => void;
}

export const Player = ({
  manifest,
  initial,
  party,
  startHighlights,
  onBack,
}: Props) => {
  const partyRef = useRef(party);
  partyRef.current = party;
  const player = useRef<VideoPlayer | null>(null);
  const audio = useRef<AudioPlayer | null>(null);
  const speakId = useRef(0);
  const switchId = useRef(0);
  const switchingNow = useRef(false);
  const [track, setTrack] = useState(initial);
  const trackRef = useRef(initial);
  trackRef.current = track;
  const [t, setT] = useState(0);
  const tRef = useRef(0);
  tRef.current = t;
  const pendingSeek = useRef<number | null>(null);
  const replayingRef = useRef(false);
  const [replaying, setReplaying] = useState(false);
  const [reel, setReel] = useState(false);
  const [showMap, setShowMap] = useState(false);
  const [code, setCode] = useState<string | null>(null);
  // Once a Why/recap card has closed, D-pad focus goes back to "Why?".
  const [refocusWhy, setRefocusWhy] = useState(false);
  // Bumped to remount "Why?" so it takes focus when the focused Replay button disappears.
  const [whyKey, setWhyKey] = useState(0);
  const replayFocused = useRef(false);
  // A talk answer that arrives mid-replay waits here until the replay ends.
  const pendingAnswer = useRef<TalkAnswer | null>(null);
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
      if (startHighlights && manifest.highlights) {
        api.current.highlights(true);
      } else {
        v.src = initial.src;
        v.play();
        log(`play ${initial.id}`);
      }
      // ponytail: poll instead of timeupdate, which may not fire reliably
      poll = setInterval(() => {
        if (!switchingNow.current && !replayingRef.current) {
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
    // eslint-disable-next-line react-hooks/exhaustive-deps -- startHighlights is read once, at mount
  }, [initial]);

  // Close the Why/recap card, stop its audio and resume the game.
  const closeOverlay = (how: string) => {
    if (!overlayRef.current) {
      return;
    }
    speakId.current++;
    audio.current?.pause();
    if (overlayRef.current.kind !== 'answer') {
      setRefocusWhy(true);
    }
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
    if (!v || overlayRef.current || replayingRef.current) {
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
    if (!v || overlayRef.current || replayingRef.current) {
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

  // Option 2c from spike S2: new src, then seek to `at`. A seek made meanwhile is queued.
  const loadSrc = (
    src: string,
    at: number,
    what: string,
    then?: () => void,
  ) => {
    const v = player.current;
    if (!v) {
      return;
    }
    const id = ++switchId.current;
    const started = Date.now();
    const finish = (how: string) => {
      if (id !== switchId.current || !switchingNow.current) {
        return;
      }
      switchingNow.current = false;
      setSwitching(null);
      log(
        `${how} ${what} t=${v.currentTime.toFixed(2)} at=${at.toFixed(
          2,
        )} after ${Date.now() - started}ms`,
      );
      const q = pendingSeek.current;
      if (q !== null) {
        pendingSeek.current = null;
        v.currentTime = q;
        log(`queued seek ${q} applied`);
      }
      then?.();
    };
    switchingNow.current = true;
    once(v, 'loadedmetadata', () => {
      if (id !== switchId.current) {
        return;
      }
      // ponytail: seeking to 0 may never fire 'seeked', so a replay waits for 'playing'
      once(v, at > 0 ? 'seeked' : 'playing', () =>
        finish(at > 0 ? 'seeked' : 'playing'),
      );
      if (at > 0) {
        v.currentTime = at;
      }
      v.play();
    });
    v.src = src;
    // ponytail: drop the overlay if seeked never arrives
    setTimeout(() => finish('switch timeout'), 10000);
  };

  const seek = (s: number) => {
    const v = player.current;
    if (!v) {
      return;
    }
    if (switchingNow.current) {
      pendingSeek.current = s;
      log(`seek ${s} queued (switch in progress)`);
      return;
    }
    v.currentTime = s;
    log(`seek ${s}`);
  };

  const switchTo = (next: Track) => {
    const v = player.current;
    if (!v || next.id === track.id || replayingRef.current) {
      return;
    }
    const saved = v.currentTime;
    setTrack(next);
    setSwitching(trackName(next));
    log(`switch to ${next.id} at t=${saved.toFixed(2)}`);
    loadSrc(next.src, saved, next.id);
  };

  // Play the pre-rendered replay clip, then return to the main track at the saved time.
  const replay = () => {
    const v = player.current;
    if (
      !v ||
      overlayRef.current ||
      replayingRef.current ||
      switchingNow.current
    ) {
      return;
    }
    const saved = v.currentTime;
    const r = replayAt(manifest, saved);
    if (!r) {
      showToast('No replay here');
      return;
    }
    replayingRef.current = true;
    setReplaying(true);
    log(`replay ${r.eventId} at t=${saved.toFixed(2)} -> ${r.src}`);
    loadSrc(r.src, 0, `replay ${r.eventId}`, () =>
      setTimeout(() => {
        const back = trackRef.current;
        loadSrc(back.src, saved, `replay back ${back.id}`, () => {
          replayingRef.current = false;
          setReplaying(false);
          const a = pendingAnswer.current;
          if (a) {
            pendingAnswer.current = null;
            log('talk answer released after replay');
            api.current.hear(a);
          }
        });
      }, r.duration * 1000),
    );
  };

  // C3 highlights: the reel full-screen through the same src swap, then back to the track at the saved time
  // (or, opened from Home, back to Home).
  const highlights = (exitAfter = false) => {
    const v = player.current;
    const h = manifest.highlights;
    if (
      !v ||
      !h ||
      overlayRef.current ||
      replayingRef.current ||
      switchingNow.current
    ) {
      return;
    }
    const saved = v.currentTime;
    const started = Date.now();
    replayingRef.current = true;
    setReel(true);
    log(`highlights at t=${saved.toFixed(2)} -> ${h.src}`);
    loadSrc(h.src, 0, 'highlights', () => {
      let done = false;
      const finish = (how: string) => {
        if (done) {
          return;
        }
        done = true;
        if (player.current !== v) {
          return; // left the Player meanwhile
        }
        log(`highlights ${how} after ${Date.now() - started}ms`);
        const release = () => {
          replayingRef.current = false;
          setReel(false);
        };
        if (exitAfter) {
          release();
          onBack();
          return;
        }
        const back = trackRef.current;
        loadSrc(back.src, saved, `highlights back ${back.id}`, release);
      };
      once(v, 'ended', () => finish('ended'));
      // ponytail: in case 'ended' never fires on the VVD
      setTimeout(() => finish('timeout'), (h.duration + 5) * 1000);
    });
  };

  // C4 answer from the phone: pause the game, caption it, voice it, then resume.
  const hear = (a: TalkAnswer) => {
    const v = player.current;
    if (!v) {
      return;
    }
    if (replayingRef.current) {
      pendingAnswer.current = a;
      log(`talk answer queued until replay ends "${a.text}"`);
      return;
    }
    // ponytail: pause rather than duck, same as recap
    v.pause();
    setOverlay({kind: 'answer', text: a.text});
    log(`talk answer -> ${a.audioUrl}`);
    speak(a.audioUrl, 'talk');
  };

  useEffect(
    () =>
      connectTalk({
        url: manifest.talk?.wsUrl ?? TALK_WS_URL,
        clipId: manifest.clipId,
        playhead: () => ({
          t: tRef.current,
          trackId: trackRef.current.id,
          paused: player.current?.paused ?? true,
        }),
        onCode: setCode,
        onAnswer: (a) => api.current.hear(a),
        log,
      }),
    [manifest],
  );

  // C6: the TV's playhead settles the room's predictions.
  useEffect(() => {
    const tick = setInterval(
      () =>
        partyRef.current?.send({
          type: 'playhead',
          t: Math.max(0, tRef.current),
          trackId: trackRef.current.id,
          paused: player.current?.paused ?? true,
        }),
      1000,
    );
    return () => clearInterval(tick);
  }, []);

  const openPredict = () => {
    if (!overlayRef.current) {
      setOverlay({kind: 'predict'});
      log(`predict open t=${tRef.current.toFixed(2)}`);
    }
  };
  const predict = (value: string) => {
    party?.send({type: 'predict', kind: 'next_score_team', value});
    log(`predict ${value} t=${tRef.current.toFixed(2)}`);
    closeOverlay('predict');
    showToast(`You called ${value[0].toUpperCase()}${value.slice(1)}`);
  };

  // Autopilot calls through a ref so it always sees the latest render's state.
  const api = useRef({
    why,
    pick,
    catchUp,
    switchTo,
    replay,
    hear,
    seek,
    highlights,
  });
  api.current = {why, pick, catchUp, switchTo, replay, hear, seek, highlights};
  useEffect(() => {
    if (!AUTOPILOT) {
      return;
    }
    let alive = true;
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
      [12000, () => seek(64)],
      [4000, () => api.current.replay()], // e3 at 63.5 has the fixture replay
      [14000, () => setShowMap(true)],
      [6000, () => booth && api.current.switchTo(booth)],
      [300, () => seek(200)], // lands mid-switch: must be queued
      [16000, () => setShowMap(false)],
      [1000, () => log('auto done')],
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

  const frame =
    showMap && manifest.minimap ? activeAt(manifest.minimap.frames, t) : null;
  const replayHere =
    !!manifest.replays && (replaying || !!replayAt(manifest, t));
  const panelOpen = !!overlay && overlay.kind !== 'answer';

  useEffect(() => {
    // ponytail: log every 10th frame (5 s at 2 Hz) as evidence the map moves
    if (frame && Math.round(frame.t * 2) % 10 === 0) {
      const b = frame.ball;
      log(
        `minimap t=${frame.t} players=${frame.players.length} ball=${
          b ? `${b.x.toFixed(1)},${b.y.toFixed(1)}` : 'none'
        }`,
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [frame?.t]);
  useEffect(() => {
    log(`replay control ${replayHere ? 'shown' : 'hidden'} t=${t.toFixed(2)}`);
    if (!replayHere && replayFocused.current) {
      replayFocused.current = false;
      setRefocusWhy(true);
      setWhyKey((k) => k + 1);
      log('replay gone while focused, focus back to Why?');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [replayHere]);

  const scoreText = score
    ? Object.entries(score)
        .map(([k, v]) => `${k} ${v}`)
        .join(' - ')
    : '';
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
          {Object.entries(score).map(([k, v]) => (
            <Text
              key={k}
              style={[
                styles.team,
                {backgroundColor: team(k).bg, color: team(k).ink},
              ]}>
              {k.toUpperCase()} {v}
            </Text>
          ))}
        </View>
      )}
      {code && (
        <View style={styles.badge}>
          <Text style={styles.badgeText}>Ask on your phone: {code}</Text>
        </View>
      )}
      {party && (
        <View style={styles.party}>
          <Text style={styles.badgeText}>
            Party {party.code}:{' '}
            {party.members.map((m) => `${m.name} ${m.points}`).join(' · ')}
          </Text>
        </View>
      )}
      {party?.banner && (
        <View style={styles.banner}>
          <Text style={styles.switchingText}>{party.banner}</Text>
        </View>
      )}
      {frame && (
        <View style={styles.map}>
          <View style={styles.midline} />
          {frame.players.map((p) => (
            <View
              key={p.id}
              style={[
                styles.dot,
                {
                  left: (p.x / COURT.w) * MAP_W - s(8),
                  top: (p.y / COURT.h) * MAP_H - s(8),
                  backgroundColor: team(p.team).bg,
                },
              ]}
            />
          ))}
          {frame.ball && (
            <View
              style={[
                styles.ball,
                {
                  left: (frame.ball.x / COURT.w) * MAP_W - s(6),
                  top: (frame.ball.y / COURT.h) * MAP_H - s(6),
                },
              ]}
            />
          )}
        </View>
      )}
      {(replaying || reel) && (
        <View style={styles.replayTag}>
          <Text style={styles.role}>{reel ? 'HIGHLIGHTS' : 'REPLAY'}</Text>
        </View>
      )}
      {card && !overlay && (
        <View style={[styles.card, frame ? styles.cardLow : null]}>
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
      {overlay?.kind === 'answer' && (
        <View style={styles.caption}>
          <Text style={styles.role}>{ROLE.analyst}</Text>
          <Text style={styles.captionText}>{overlay.text}</Text>
        </View>
      )}
      {overlay && overlay.kind !== 'answer' && (
        <View style={styles.panel}>
          <Text style={styles.cardTitle}>
            {overlay.kind === 'why'
              ? 'Why?'
              : overlay.kind === 'predict'
              ? 'Next basket:'
              : 'Catch me up'}
          </Text>
          {overlay.kind === 'predict' ? (
            <View style={styles.row}>
              {Object.keys(manifest.state[0]?.score ?? {}).map((k, i) => (
                <FocusButton
                  key={k}
                  label={`${k[0].toUpperCase()}${k.slice(1)}`}
                  onPress={() => predict(k)}
                  hasTVPreferredFocus={i === 0}
                />
              ))}
            </View>
          ) : overlay.kind === 'why' && !overlay.answer ? (
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
      {/* next: fantasy panel */}
      {/* ponytail: the bar unmounts while a panel is open, so D-pad focus can't leave the panel */}
      {!panelOpen && (
        <View style={styles.bar}>
          <FocusButton
            key={`why${whyKey}`}
            label="Why?"
            onPress={why}
            hasTVPreferredFocus={refocusWhy && !panelOpen}
          />
          <FocusButton label="Catch me up" onPress={catchUp} />
          {party && <FocusButton label="Predict" onPress={openPredict} />}
          {manifest.tracks.map((tr) => (
            <FocusButton
              key={tr.id}
              label={trackName(tr)}
              selected={tr.id === track.id}
              onPress={() => switchTo(tr)}
              hasTVPreferredFocus={!refocusWhy && tr.id === initial.id}
            />
          ))}
          {manifest.minimap && (
            <FocusButton
              label="Map"
              selected={showMap}
              onPress={() => setShowMap((on) => !on)}
            />
          )}
          {manifest.highlights && (
            <FocusButton
              label={reel ? 'Highlights…' : 'Highlights'}
              onPress={() => highlights()}
            />
          )}
          {/* ponytail: last in the bar so showing/hiding it doesn't shift the others */}
          {replayHere && (
            <FocusButton
              label={replaying ? 'Replaying…' : 'Replay'}
              onPress={replay}
              onFocusChange={(f) => {
                replayFocused.current = f;
              }}
            />
          )}
        </View>
      )}
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
    backgroundColor: C.glass,
    borderWidth: 2,
    borderColor: C.line,
    borderRadius: s(12),
    overflow: 'hidden',
  },
  team: {
    color: C.text,
    fontSize: s(40),
    fontWeight: '800',
    paddingVertical: s(10),
    paddingHorizontal: s(24),
  },
  card: {
    position: 'absolute',
    top: '5%',
    right: '5%',
    width: '38%',
    padding: s(28),
    borderRadius: s(16),
    backgroundColor: C.glass,
    borderWidth: 2,
    borderColor: C.line,
    borderLeftWidth: s(8),
    borderLeftColor: C.accent,
  },
  cardLow: {top: '32%'},
  badge: {
    position: 'absolute',
    top: '14%',
    left: '5%',
    paddingVertical: s(8),
    paddingHorizontal: s(16),
    borderRadius: s(10),
    backgroundColor: C.glass,
    borderWidth: 2,
    borderColor: C.line,
  },
  party: {
    position: 'absolute',
    top: '21%',
    left: '5%',
    paddingVertical: s(8),
    paddingHorizontal: s(16),
    borderRadius: s(10),
    backgroundColor: C.glass,
    borderWidth: 2,
    borderColor: C.line,
  },
  banner: {
    position: 'absolute',
    top: '30%',
    alignSelf: 'center',
    paddingVertical: s(20),
    paddingHorizontal: s(40),
    borderRadius: s(16),
    backgroundColor: 'rgba(214,36,122,0.92)',
  },
  row: {flexDirection: 'row', marginTop: s(16)},
  badgeText: {color: C.text, fontSize: s(26), fontWeight: '600'},
  map: {
    position: 'absolute',
    top: '5%',
    right: '5%',
    width: MAP_W,
    height: MAP_H,
    borderWidth: 3,
    borderColor: C.lineStrong,
    backgroundColor: 'rgba(12,40,28,0.88)',
    borderRadius: s(12),
    overflow: 'hidden',
  },
  midline: {
    position: 'absolute',
    left: MAP_W / 2 - 1,
    top: 0,
    bottom: 0,
    width: s(2),
    backgroundColor: '#FFFFFF',
  },
  dot: {position: 'absolute', width: s(16), height: s(16), borderRadius: s(8)},
  ball: {
    position: 'absolute',
    width: s(12),
    height: s(12),
    borderRadius: s(6),
    backgroundColor: '#FF9900',
    borderWidth: 1,
    borderColor: '#000',
  },
  replayTag: {
    position: 'absolute',
    top: '5%',
    alignSelf: 'center',
    paddingVertical: s(8),
    paddingHorizontal: s(20),
    borderRadius: s(10),
    backgroundColor: C.glass,
    borderWidth: 2,
    borderColor: C.line,
  },
  panel: {
    position: 'absolute',
    top: '18%',
    left: '5%',
    width: '55%',
    padding: s(32),
    borderRadius: s(16),
    backgroundColor: C.glass,
    borderWidth: 2,
    borderColor: C.line,
    borderLeftWidth: s(8),
    borderLeftColor: C.accent,
    alignItems: 'flex-start',
  },
  cardTitle: {color: C.accent, fontSize: s(40), fontWeight: '800'},
  cardBody: {
    color: C.text,
    fontSize: s(30),
    lineHeight: s(40),
    marginTop: s(12),
    marginBottom: s(20),
  },
  caption: {
    position: 'absolute',
    bottom: '20%',
    left: '10%',
    right: '10%',
    padding: s(20),
    borderRadius: s(12),
    backgroundColor: C.glass,
    borderWidth: 2,
    borderColor: C.line,
  },
  role: {...eyebrow, color: C.accent},
  captionText: {color: C.text, fontSize: s(34), lineHeight: s(44), marginTop: s(6)},
  switching: {
    position: 'absolute',
    top: '42%',
    alignSelf: 'center',
    paddingVertical: s(24),
    paddingHorizontal: s(48),
    borderRadius: s(16),
    backgroundColor: C.glass,
    borderWidth: 2,
    borderColor: C.lineStrong,
  },
  switchingText: {color: C.text, fontSize: s(48), fontWeight: '700'},
  bar: {
    position: 'absolute',
    bottom: '4%',
    left: '5%',
    right: '5%',
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
});
