import React, {useEffect, useRef, useState} from 'react';
import {BackHandler, StyleSheet, Text, View} from 'react-native';
import {
  KeplerVideoSurfaceView,
  VideoPlayer,
} from '@amazon-devices/react-native-w3cmedia';
import {FocusButton} from '../components/FocusButton';
import {Manifest, Track, activeAt, trackName} from '../manifest';

const TEACHABLE = new Set(['foul', 'travel', 'turnover', 'made_3', 'ft_made']);
const CARD_SECS = 6;
// console.warn: info level is suppressed for the first seconds after launch
const log = (msg: string) => console.warn(`YOC: ${msg}`);

const once = (v: VideoPlayer, type: string, fn: () => void) => {
  const h = () => {
    v.removeEventListener(type, h);
    fn();
  };
  v.addEventListener(type, h);
};

interface Props {
  manifest: Manifest;
  initial: Track;
  onBack: () => void;
}

export const Player = ({manifest, initial, onBack}: Props) => {
  const player = useRef<VideoPlayer | null>(null);
  const switchId = useRef(0);
  const switchingNow = useRef(false);
  const [track, setTrack] = useState(initial);
  const [t, setT] = useState(0);
  const [switching, setSwitching] = useState<string | null>(null);
  const surface = useRef<(h: string) => void>(() => {});
  const surfaceReady = useRef(
    new Promise<string>((r) => {
      surface.current = r;
    }),
  );

  useEffect(() => {
    const v = new VideoPlayer();
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
    })().catch((e) => log(`FATAL ${e}`));
    return () => {
      alive = false;
      clearInterval(poll);
      player.current = null;
      v.pause();
      v.deinitialize().catch(() => {});
    };
  }, [initial]);

  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', () => {
      log('back');
      onBack();
      return true;
    });
    return () => sub.remove();
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
      {card && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>{card.title}</Text>
          <Text style={styles.cardBody}>{card.body}</Text>
        </View>
      )}
      {switching && (
        <View style={styles.switching}>
          <Text style={styles.switchingText}>Switching to {switching}…</Text>
        </View>
      )}
      {/* next: fantasy panel (right edge) and Why button (bottom bar) */}
      <View style={styles.bar}>
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
  cardTitle: {color: '#FFD400', fontSize: 44, fontWeight: '700'},
  cardBody: {color: '#FFFFFF', fontSize: 30, lineHeight: 40, marginTop: 12},
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
  },
});
