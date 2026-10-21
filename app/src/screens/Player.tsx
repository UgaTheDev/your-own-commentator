import React, {useEffect, useMemo, useRef, useState} from 'react';
import {BackHandler, StyleSheet, Text, View} from 'react-native';
import {useTVEventHandler} from '@amazon-devices/react-native-kepler';
import {
  AudioPlayer,
  KeplerVideoSurfaceView,
  VideoPlayer,
} from '@amazon-devices/react-native-w3cmedia';
import {FocusButton} from '../components/FocusButton';
import {C, SAFE, T, eyebrow, personaOf, s, team} from '../theme';
import {PersonaIcon} from '../components/Brand';
import {
  Caption,
  CodeBadge,
  MiniMap,
  ModeTag,
  PausedPill,
  PhoneRow,
  Play,
  RuleCard,
  ScoreBug,
  SwitchCard,
  TeamChip,
  glass,
} from '../components/player/Overlays';
import {
  PTS,
  eventLabel,
  flashAt,
  playLabel,
  teamTag,
} from '../components/player/labels';
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
// Strip / tray name without the bracketed language.
const shortName = (tr: Track) => trackName(tr).replace(/\s*\(.*\)$/, '');
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
  | {
      kind: 'why';
      eventId: string;
      questions: Question[];
      answer?: string;
      q?: string;
    }
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
  const [replayEvent, setReplayEvent] = useState<string | null>(null);
  const [reel, setReel] = useState(false);
  const [showMap, setShowMap] = useState(false);
  const [code, setCode] = useState<string | null>(null);
  // Which strip button takes D-pad focus: the commentator button at start and after the tray closes,
  // "Why?" once a Why/recap card has closed.
  const [refocus, setRefocus] = useState<'why' | 'voice'>('voice');
  // Bumped to remount "Why?" so it takes focus when the focused Replay button disappears.
  const [whyKey, setWhyKey] = useState(0);
  // 3c commentator tray; bumped key remounts the strip button so focus returns to it on close.
  const [tray, setTrayState] = useState(false);
  const trayRef = useRef(false);
  const [voiceKey, setVoiceKey] = useState(0);
  const setTray = (open: boolean, refocusVoice = false) => {
    trayRef.current = open;
    setTrayState(open);
    if (refocusVoice) {
      setRefocus('voice');
      setVoiceKey((k) => k + 1);
    }
  };
  const replayFocused = useRef(false);
  // A talk answer that arrives mid-replay waits here until the replay ends.
  const pendingAnswer = useRef<TalkAnswer | null>(null);
  const [switching, setSwitching] = useState<{from: Track; to: Track} | null>(
    null,
  );
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
      let ticks = 0;
      poll = setInterval(() => {
        if (!switchingNow.current && !replayingRef.current) {
          setT(v.currentTime);
          // 1 Hz game clock for scripts/demo (works without the talk relay's playhead heartbeat)
          if (++ticks % 4 === 0) {
            log(`tick t=${v.currentTime.toFixed(2)}`);
          }
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
      setRefocus('why');
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
    setOverlay({...o, answer: ans.text, q: q.q});
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
      if (trayRef.current) {
        setTray(false, true);
        log('tray closed (back)');
      } else if (overlayRef.current) {
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

  const seek = (sec: number) => {
    const v = player.current;
    if (!v) {
      return;
    }
    if (switchingNow.current) {
      pendingSeek.current = sec;
      log(`seek ${sec} queued (switch in progress)`);
      return;
    }
    v.currentTime = sec;
    log(`seek ${sec}`);
  };

  const switchTo = (next: Track) => {
    const v = player.current;
    if (!v || next.id === track.id || replayingRef.current) {
      return;
    }
    const saved = v.currentTime;
    setTrack(next);
    setSwitching({from: track, to: next});
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
    setReplayEvent(r.eventId);
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
  // Remote rewind: back 10 s, e.g. to hear the same play again from another commentator.
  useTVEventHandler((e) => {
    const v = player.current;
    if (
      v &&
      (e.eventType === 'rewind' || e.eventType === 'skip_backward') &&
      e.eventKeyAction !== 1 &&
      !replayingRef.current
    ) {
      seek(Math.max(0, v.currentTime - 10));
    }
  });
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
    // t is clip time during a replay or the reel, so game-time minimap frames would be the wrong play
    showMap && manifest.minimap && !replaying && !reel
      ? activeAt(manifest.minimap.frames, t)
      : null;
  const replayHere =
    !!manifest.replays && (replaying || !!replayAt(manifest, t));
  const panelOpen = !!overlay && overlay.kind !== 'answer';
  const scoring = useMemo(
    () => manifest.events.filter((e) => PTS[e.type] && e.team),
    [manifest],
  );
  const flash = flashAt(scoring, t);
  const persona = personaOf(track.id);
  const name = shortName(track);
  const teams = Object.keys(manifest.state[0]?.score ?? {});
  const evById = (id: string | null) =>
    manifest.events.find((e) => e.id === id) ?? null;
  const replayEv = replaying ? evById(replayEvent) : null;
  const replayLabel = replayEv ? eventLabel(replayEv) : null;
  // ponytail: the banner text carries no team, so its colour comes from the latest basket at the playhead
  const lastBasket = party?.banner ? flashAt(scoring, t, Infinity) : null;
  const trayOpen = tray && !panelOpen;
  // Strip focus moving down/sideways out of the tray closes it (▼ closes, per 3c).
  const stripFocus = (f: boolean) => {
    if (f && trayRef.current) {
      setTray(false);
      log('tray closed (focus)');
    }
  };

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
      setRefocus('why');
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

  const whyEv = overlay?.kind === 'why' ? evById(overlay.eventId) : null;
  const whyTag = whyEv ? teamTag(whyEv) : null;
  const whyCard = whyEv?.ruleCardId
    ? manifest.ruleCards[whyEv.ruleCardId]
    : undefined;
  // "Replay play" only when the playhead's replay is this Why's play (replay() picks by playhead).
  const whyReplay = !!whyEv && replayAt(manifest, t)?.eventId === whyEv.id;
  const resume = (text: string, primary = true, focus = true) => (
    <FocusButton
      label="Back to game"
      primary={primary}
      onPress={() => closeOverlay('button')}
      hasTVPreferredFocus={focus}
      style={styles.panelBtn}>
      <View style={styles.btnRow}>
        <Play color={primary ? C.accentInk : C.text} />
        <Text style={[styles.btnText, primary && {color: C.accentInk}]}>
          {text}
        </Text>
      </View>
    </FocusButton>
  );

  return (
    <View style={styles.root}>
      <KeplerVideoSurfaceView
        style={styles.video}
        onSurfaceViewCreated={(h: string) => surface.current(h)}
        onSurfaceViewDestroyed={(h: string) =>
          player.current?.clearSurfaceHandle(h)
        }
      />
      {/* dim: 25% while switching (3d), 50% while Why?/Catch me up pause the game (4a-4c) */}
      {(switching || overlay?.kind === 'why' || overlay?.kind === 'recap') && (
        <View
          pointerEvents="none"
          style={[
            styles.video,
            {backgroundColor: `rgba(0,0,0,${switching ? 0.25 : 0.5})`},
          ]}
        />
      )}
      {replaying && <View pointerEvents="none" style={styles.replayFrame} />}
      {score && <ScoreBug score={score} flash={flash} />}
      {(overlay?.kind === 'why' || overlay?.kind === 'recap') && <PausedPill />}
      {code && !panelOpen && <CodeBadge code={code} />}
      {party && !panelOpen && (
        <View style={[styles.party, glass]}>
          <Text style={styles.partyText}>
            Party <Text style={styles.accentBold}>{party.code}</Text>
            {party.members.length
              ? ` · ${party.members
                  .map((m) => `${m.name} ${m.points}`)
                  .join(' · ')}`
              : ''}
          </Text>
        </View>
      )}
      {(replaying || reel) && (
        <ModeTag kind={reel ? 'highlights' : 'replay'} detail={replayLabel} />
      )}
      {card && !overlay && ev && (
        <RuleCard
          title={card.title}
          body={card.body}
          left={1 - (t - ev.t) / CARD_SECS}
        />
      )}
      {frame && !trayOpen && <MiniMap frame={frame} />}
      {caption && !overlay && !trayOpen && !switching && (
        <Caption
          persona={persona}
          role={caption.role}
          speaker={name}
          text={caption.text}
        />
      )}
      {overlay?.kind === 'answer' && !trayOpen && (
        <Caption
          persona={persona}
          role="analyst"
          speaker={name}
          text={overlay.text}
        />
      )}
      {overlay?.kind === 'why' && (
        <View style={[styles.side, glass]}>
          {!overlay.answer ? (
            <>
              <View style={styles.eyebrowRow}>
                <View style={styles.qDisc}>
                  <Text style={styles.qDiscText}>?</Text>
                </View>
                <Text style={[eyebrow, {color: C.accent}]}>
                  WHY? · ABOUT THIS PLAY
                </Text>
              </View>
              {whyEv && (
                <View style={styles.context}>
                  {whyEv.team && whyTag && (
                    <TeamChip name={whyEv.team} text={whyTag.toUpperCase()} />
                  )}
                  <Text style={styles.soft}>{playLabel(whyEv.type)}</Text>
                </View>
              )}
              <Text style={styles.h2}>What do you want to know?</Text>
              <View style={styles.questions}>
                {overlay.questions.map((q, i) => (
                  <FocusButton
                    key={q.q}
                    label={q.q}
                    onPress={() => pick(q)}
                    hasTVPreferredFocus={i === 0}
                    style={styles.question}>
                    <View style={styles.btnRow}>
                      <Text style={styles.qNum}>{i + 1}</Text>
                      <Text style={styles.qText}>{q.q}</Text>
                    </View>
                  </FocusButton>
                ))}
              </View>
              {code && <PhoneRow code={code} />}
              <View style={styles.bottom}>
                {resume('Resume game', false, false)}
              </View>
            </>
          ) : (
            <>
              <View style={styles.answerHead}>
                <View style={styles.eyebrowRow}>
                  <PersonaIcon persona={persona} size={s(56)} />
                  <Text style={[eyebrow, {color: C.accent}]}>
                    {name.toUpperCase()} ANSWERS
                  </Text>
                </View>
                <View style={styles.wave}>
                  {[14, 30, 40, 22, 34, 16, 26].map((h, i) => (
                    <View key={i} style={[styles.waveBar, {height: s(h)}]} />
                  ))}
                </View>
              </View>
              {overlay.q && <Text style={styles.echo}>“{overlay.q}”</Text>}
              <Text style={styles.answer}>{overlay.answer}</Text>
              <View style={styles.checked}>
                <Text style={eyebrow}>CHECKED AGAINST</Text>
                {[
                  'Verified play log',
                  'Game score',
                  ...(whyCard ? [`Rule card: ${whyCard.title}`] : []),
                ].map((src) => (
                  <View key={src} style={styles.btnRow}>
                    <Text style={styles.tick}>✓</Text>
                    <Text style={styles.sourceText}>{src}</Text>
                  </View>
                ))}
              </View>
              <View style={[styles.bottom, styles.btnRow]}>
                {resume('Resume')}
                {whyReplay && (
                  <FocusButton
                    label="Replay play"
                    onPress={() => {
                      closeOverlay('replay');
                      replay();
                    }}
                    style={styles.panelBtn}
                  />
                )}
              </View>
            </>
          )}
        </View>
      )}
      {overlay?.kind === 'recap' && (
        <View style={[styles.recap, glass]}>
          <View style={styles.answerHead}>
            <Text style={[eyebrow, {color: C.accent}]}>
              CATCH ME UP · LAST 2 MIN
            </Text>
            <View style={styles.eyebrowRow}>
              <PersonaIcon persona={persona} size={s(44)} />
              <Text style={styles.mutedText}>{name}</Text>
            </View>
          </View>
          <Text style={styles.answer}>{overlay.text}</Text>
          <View style={styles.btnRow}>{resume('Back to live')}</View>
        </View>
      )}
      {overlay?.kind === 'predict' && (
        <View style={[styles.predict, glass]}>
          <Text style={[eyebrow, {color: C.accent}]}>PREDICT</Text>
          <Text style={styles.predictH}>
            Next basket:{' '}
            {teams
              .map((k) => `${k[0].toUpperCase()}${k.slice(1)}`)
              .join(' or ')}
            ?
          </Text>
          <View style={styles.btnRow}>
            {teams.map((k, i) => (
              <FocusButton
                key={k}
                label={`${k[0].toUpperCase()}${k.slice(1)}`}
                onPress={() => predict(k)}
                hasTVPreferredFocus={i === 0}
                outerStyle={styles.flex}
                style={styles.teamBtn}>
                <View style={[styles.teamFill, {backgroundColor: team(k).bg}]}>
                  <Text style={[styles.teamName, {color: team(k).ink}]}>
                    {k.toUpperCase()}
                  </Text>
                </View>
              </FocusButton>
            ))}
          </View>
        </View>
      )}
      {party?.banner && (
        <View
          style={[
            styles.banner,
            lastBasket ? {backgroundColor: team(lastBasket.team).bg} : glass,
          ]}>
          {lastBasket && lastBasket.pts > 0 && (
            <View style={styles.bannerPts}>
              <Text style={styles.bannerBig}>+{lastBasket.pts}</Text>
              <Text style={styles.bannerTeam}>
                {lastBasket.team.toUpperCase()}
              </Text>
            </View>
          )}
          <Text
            style={[
              styles.bannerText,
              {color: lastBasket ? team(lastBasket.team).ink : C.text},
            ]}>
            {party.banner}
          </Text>
        </View>
      )}
      {toast && (
        <View style={styles.toastWrap} pointerEvents="none">
          <View style={[styles.toast, glass]}>
            <Text style={styles.toastText}>{toast}</Text>
          </View>
        </View>
      )}
      {switching && (
        <SwitchCard
          key={switching.to.id}
          from={personaOf(switching.from.id)}
          to={personaOf(switching.to.id)}
          name={shortName(switching.to)}
        />
      )}
      {trayOpen && (
        <View style={[styles.tray, glass]}>
          {manifest.tracks.map((tr) => {
            const onAir = tr.id === track.id;
            return (
              <FocusButton
                key={tr.id}
                label={shortName(tr)}
                card
                onPress={() => {
                  switchTo(tr);
                  setTray(false, true);
                }}
                hasTVPreferredFocus={onAir}
                outerStyle={styles.flex}
                style={[styles.trayItem, onAir && styles.onAirItem]}>
                <View style={styles.trayRow}>
                  <PersonaIcon persona={personaOf(tr.id)} size={s(60)} />
                  <View style={styles.flex}>
                    <Text style={styles.trayName} numberOfLines={1}>
                      {shortName(tr)}
                    </Text>
                    <Text
                      style={onAir ? styles.onAirText : styles.mutedText}
                      numberOfLines={1}>
                      {onAir ? '● ON AIR' : tr.lang.toUpperCase()}
                    </Text>
                  </View>
                </View>
              </FocusButton>
            );
          })}
        </View>
      )}
      {/* bottom scrim (handoff: 0 -> rgba(7,11,16,.92) over the bottom ~300 px) behind captions and the strip;
          it also hides the broadcast's own score graphic under the strip */}
      <View pointerEvents="none" style={styles.scrim}>
        {Array.from({length: 40}, (_, i) => (
          <View
            key={i}
            style={{
              flex: 1,
              backgroundColor: `rgba(7,11,16,${(
                0.97 *
                ((i + 0.5) / 40) ** 0.9
              ).toFixed(3)})`,
            }}
          />
        ))}
      </View>
      {/* ponytail: the strip unmounts while a panel is open, so D-pad focus can't leave the panel;
          it never auto-hides (Vega gives no reliable key event to bring it back) */}
      {!panelOpen && (
        <View style={[styles.strip, glass]}>
          <FocusButton
            key={`why${whyKey}`}
            label="Why?"
            primary
            onPress={why}
            onFocusChange={stripFocus}
            hasTVPreferredFocus={refocus === 'why' && !panelOpen}
            outerStyle={styles.stripBtn}>
            <View style={styles.btnRow}>
              <View style={styles.whyDisc}>
                <Text style={styles.whyDiscText}>?</Text>
              </View>
              <Text style={[styles.btnText, {color: C.accentInk}]}>Why?</Text>
            </View>
          </FocusButton>
          <FocusButton
            label="Catch me up"
            onPress={catchUp}
            onFocusChange={stripFocus}
            outerStyle={styles.stripBtn}
          />
          {party && (
            <FocusButton
              label="Predict"
              onPress={openPredict}
              onFocusChange={stripFocus}
              outerStyle={styles.stripBtn}
            />
          )}
          <FocusButton
            key={`voice${voiceKey}`}
            label="Commentators"
            selected={trayOpen}
            onPress={() => setTray(!trayRef.current, trayRef.current)}
            onFocusChange={stripFocus}
            hasTVPreferredFocus={refocus === 'voice' && !trayOpen}
            outerStyle={styles.stripBtn}
            style={styles.voiceBtn}>
            <View style={styles.btnRow}>
              <PersonaIcon persona={persona} size={s(48)} />
              <Text style={[styles.btnText, trayOpen && {color: C.accent}]}>
                {name} ▲
              </Text>
            </View>
          </FocusButton>
          {manifest.minimap && (
            <FocusButton
              label="Map"
              selected={showMap}
              onPress={() => setShowMap((on) => !on)}
              onFocusChange={stripFocus}
              outerStyle={styles.stripBtn}
            />
          )}
          {manifest.highlights && (
            <FocusButton
              label={reel ? 'Highlights…' : 'Highlights'}
              onPress={() => highlights()}
              onFocusChange={stripFocus}
              outerStyle={styles.stripBtn}
            />
          )}
          {/* ponytail: last in the bar so showing/hiding it doesn't shift the others */}
          {replayHere && (
            <FocusButton
              label={replaying ? 'Replaying…' : 'Replay'}
              onPress={replay}
              onFocusChange={(f) => {
                replayFocused.current = f;
                stripFocus(f);
              }}
              outerStyle={styles.stripBtn}
            />
          )}
          <View style={styles.onAir}>
            <View style={styles.dot} />
            <Text style={styles.mutedText} numberOfLines={1}>
              On air: <Text style={styles.onAirName}>{name}</Text>
            </Text>
          </View>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  scrim: {position: 'absolute', left: 0, right: 0, bottom: 0, height: s(360)},
  root: {flex: 1, backgroundColor: '#000'},
  video: {position: 'absolute', top: 0, left: 0, right: 0, bottom: 0},
  flex: {flex: 1},
  replayFrame: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    borderWidth: s(10),
    borderColor: 'rgba(255,212,0,0.9)',
  },
  party: {
    position: 'absolute',
    right: SAFE.x,
    top: s(146),
    maxWidth: s(760),
    height: s(64),
    justifyContent: 'center',
    paddingHorizontal: s(24),
    borderRadius: s(16),
  },
  partyText: {fontSize: s(24), fontWeight: '700', color: C.text},
  accentBold: {color: C.accent, fontWeight: '800', letterSpacing: s(3.4)},
  mutedText: {...T.body, color: C.muted},
  soft: {...T.body, color: C.textSoft},
  btnRow: {flexDirection: 'row', alignItems: 'center', gap: s(14)},
  btnText: {fontSize: s(26), fontWeight: '700', color: C.text},
  panelBtn: {minHeight: s(80), paddingHorizontal: s(32)},
  side: {
    position: 'absolute',
    right: SAFE.x,
    top: SAFE.y,
    bottom: SAFE.y,
    width: s(760),
    padding: s(48),
    borderRadius: s(28),
    gap: s(20),
  },
  eyebrowRow: {flexDirection: 'row', alignItems: 'center', gap: s(14)},
  qDisc: {
    width: s(36),
    height: s(36),
    borderRadius: s(18),
    backgroundColor: C.accent,
    alignItems: 'center',
    justifyContent: 'center',
  },
  qDiscText: {fontSize: s(24), fontWeight: '800', color: C.accentInk},
  context: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: s(10),
  },
  h2: {...T.h2, color: C.text, marginTop: s(4)},
  questions: {gap: s(12), marginTop: s(8)},
  question: {minHeight: s(120), borderRadius: s(16)},
  qNum: {fontSize: s(24), fontWeight: '800', color: C.accent},
  qText: {
    flex: 1,
    fontSize: s(28),
    lineHeight: s(36),
    fontWeight: '700',
    color: C.text,
  },
  bottom: {marginTop: 'auto'},
  answerHead: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  wave: {flexDirection: 'row', alignItems: 'center', gap: s(5), height: s(40)},
  waveBar: {width: s(6), borderRadius: s(3), backgroundColor: C.accent},
  echo: {fontSize: s(26), lineHeight: s(36), color: C.muted},
  answer: {
    fontSize: s(36),
    lineHeight: s(50),
    fontWeight: '700',
    color: C.text,
  },
  checked: {
    gap: s(14),
    padding: s(24),
    borderRadius: s(20),
    backgroundColor: C.panel,
    borderWidth: 1,
    borderColor: C.line,
  },
  tick: {fontSize: s(24), fontWeight: '800', color: C.accent},
  sourceText: {
    fontSize: s(24),
    lineHeight: s(32),
    color: C.text,
    flexShrink: 1,
  },
  recap: {
    position: 'absolute',
    left: s(400),
    top: s(240),
    width: s(1120),
    paddingVertical: s(48),
    paddingHorizontal: s(56),
    borderRadius: s(28),
    gap: s(28),
  },
  predict: {
    position: 'absolute',
    left: SAFE.x,
    bottom: SAFE.y,
    width: s(1000),
    paddingVertical: s(36),
    paddingHorizontal: s(40),
    borderRadius: s(28),
    gap: s(24),
  },
  predictH: {
    fontSize: s(48),
    lineHeight: s(56),
    fontWeight: '800',
    color: C.text,
  },
  // the fill sits inside the box so FocusButton's focused background can't repaint the team colour
  teamBtn: {
    minHeight: s(120),
    paddingHorizontal: 0,
    borderWidth: 0,
    borderRadius: s(20),
    overflow: 'hidden',
  },
  teamFill: {
    flex: 1,
    minHeight: s(120),
    justifyContent: 'center',
    paddingHorizontal: s(32),
  },
  teamName: {fontSize: s(40), fontWeight: '800', letterSpacing: s(2.4)},
  banner: {
    position: 'absolute',
    left: SAFE.x,
    right: SAFE.x,
    bottom: s(166),
    height: s(200),
    borderRadius: s(28),
    overflow: 'hidden',
    flexDirection: 'row',
    alignItems: 'center',
  },
  bannerPts: {
    width: s(200),
    height: s(200),
    backgroundColor: C.accent,
    alignItems: 'center',
    justifyContent: 'center',
  },
  bannerBig: {
    fontSize: s(72),
    lineHeight: s(72),
    fontWeight: '800',
    color: C.accentInk,
  },
  bannerTeam: {...eyebrow, color: C.accentInk, fontWeight: '800'},
  bannerText: {
    flex: 1,
    paddingHorizontal: s(48),
    fontSize: s(64),
    lineHeight: s(72),
    fontWeight: '800',
  },
  toastWrap: {
    position: 'absolute',
    top: s(162),
    left: 0,
    right: 0,
    alignItems: 'center',
  },
  toast: {
    paddingVertical: s(16),
    paddingHorizontal: s(32),
    borderRadius: s(16),
  },
  toastText: {...T.title, color: C.text},
  tray: {
    position: 'absolute',
    left: SAFE.x,
    right: SAFE.x,
    bottom: s(166),
    padding: s(16),
    borderRadius: s(24),
    flexDirection: 'row',
  },
  trayItem: {minHeight: s(104), paddingHorizontal: s(16), borderRadius: s(16)},
  onAirItem: {borderWidth: s(3), borderColor: C.accent},
  trayRow: {flexDirection: 'row', alignItems: 'center', gap: s(14)},
  trayName: {
    fontSize: s(26),
    lineHeight: s(36),
    fontWeight: '800',
    color: C.text,
  },
  onAirText: {fontSize: s(24), fontWeight: '700', color: C.accent},
  strip: {
    position: 'absolute',
    left: SAFE.x,
    right: SAFE.x,
    bottom: SAFE.y,
    height: s(88),
    paddingHorizontal: s(8),
    borderRadius: s(20),
    flexDirection: 'row',
    alignItems: 'center',
  },
  stripBtn: {marginRight: s(4), marginBottom: 0},
  voiceBtn: {paddingLeft: s(12), paddingRight: s(24)},
  whyDisc: {
    width: s(34),
    height: s(34),
    borderRadius: s(17),
    backgroundColor: C.accentInk,
    alignItems: 'center',
    justifyContent: 'center',
  },
  whyDiscText: {fontSize: s(24), fontWeight: '800', color: C.accent},
  onAir: {
    marginLeft: 'auto',
    paddingRight: s(20),
    flexDirection: 'row',
    alignItems: 'center',
    gap: s(12),
    flexShrink: 1,
  },
  dot: {
    width: s(12),
    height: s(12),
    borderRadius: s(6),
    backgroundColor: C.accent,
  },
  onAirName: {color: C.text, fontWeight: '700'},
});
