// Spike S2 harness: runs the audio-switching tests on launch and logs `S2:` lines.
// Temporary; App.tsx renders it. Revert App.tsx to go back to the template.
import React, {useEffect, useRef, useState} from 'react';
import {ScrollView, StyleSheet, Text, View} from 'react-native';
import {
  AudioPlayer,
  KeplerVideoSurfaceView,
  VideoPlayer,
} from '@amazon-devices/react-native-w3cmedia';

// The Vega media player only accepts https:// media (isUriSchemeSecure rejects http).
// Per-file URLs (presigned URLs carry query strings, so no path concatenation).
const URLS: Record<string, string> = {
  'dual.mp4': 'https://REPLACE/dual.mp4',
  'a440.mp4': 'https://REPLACE/a440.mp4',
  'a880.mp4': 'https://REPLACE/a880.mp4',
  'why.mp3': 'https://REPLACE/why.mp3',
};
const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));
const t0 = Date.now();

type Player = VideoPlayer | AudioPlayer;

// Resolves with ms elapsed until `type` fires, or -1 on timeout.
const waitFor = (p: Player, type: string, timeoutMs = 10000) =>
  new Promise<number>((resolve) => {
    const start = Date.now();
    const h = () => {
      clearTimeout(timer);
      p.removeEventListener(type, h);
      resolve(Date.now() - start);
    };
    const timer = setTimeout(() => {
      p.removeEventListener(type, h);
      resolve(-1);
    }, timeoutMs);
    p.addEventListener(type, h);
  });

export const S2Spike = () => {
  const [lines, setLines] = useState<string[]>([]);
  const surface = useRef<(h: string) => void>(() => {});
  const surfaceReady = useRef(
    new Promise<string>((r) => {
      surface.current = r;
    }),
  );

  useEffect(() => {
    const log = (msg: string) => {
      const line = `S2: +${((Date.now() - t0) / 1000).toFixed(2)}s ${msg}`;
      console.warn(line); // info level is suppressed for the first seconds after launch
      setLines((l) => [...l, line]);
    };

    const run = async () => {
      const v = new VideoPlayer();
      await v.initialize();
      log('player1 initialized');
      const handle = await surfaceReady.current;
      v.setSurfaceHandle(handle);
      for (const ev of ['waiting', 'stalled', 'error', 'seeking', 'seeked']) {
        v.addEventListener(ev, () =>
          log(`p1 event ${ev} t=${v.currentTime.toFixed(3)}`),
        );
      }

      // Q1: one MP4, two audio streams, toggle audioTracks[i].enabled
      let added = 0;
      v.audioTracks.addEventListener('addtrack', () => {
        added++;
        log(`Q1 addtrack event #${added} length=${v.audioTracks.length}`);
      });
      v.src = URLS['dual.mp4'];
      const playing = waitFor(v, 'playing', 15000);
      v.play();
      log(`Q1 dual.mp4 playing after ${await playing}ms`);
      for (let i = 0; i < 8; i++) {
        await sleep(500);
        log(`Q1 poll audio=${v.audioTracks.length} video=${v.videoTracks?.length} t=${v.currentTime.toFixed(3)}`);
      }
      // ponytail: AudioTrackList typings lack an index signature
      const tracks = v.audioTracks as any;
      log(`Q1 audioTracks exists=${!!tracks} length=${tracks?.length}`);
      const dump = () => {
        const out = [];
        for (let i = 0; i < (tracks?.length ?? 0); i++) {
          const a = tracks[i];
          out.push(`[${i}] id=${a.id} label=${a.label} lang=${a.language} enabled=${a.enabled}`);
        }
        return out.join(' ');
      };
      log(`Q1 tracks ${dump()}`);
      if (tracks && tracks.length >= 2) {
        tracks.addEventListener?.('change', () => log('Q1 audioTracks change event'));
        const before = v.currentTime;
        const sw = Date.now();
        tracks[0].enabled = false;
        tracks[1].enabled = true;
        log(`Q1 SWITCH to track1 at t=${before.toFixed(3)} (set took ${Date.now() - sw}ms)`);
        for (let i = 0; i < 8; i++) {
          await sleep(250);
          log(`Q1 +${(i + 1) * 250}ms t=${v.currentTime.toFixed(3)} paused=${v.paused} rs=${v.readyState}`);
        }
        log(`Q1 after switch ${dump()}`);
        await sleep(3000);
        tracks[1].enabled = false;
        tracks[0].enabled = true;
        log(`Q1 SWITCH back to track0 at t=${v.currentTime.toFixed(3)}`);
        await sleep(3000);
        log(`Q1 after switch back ${dump()} t=${v.currentTime.toFixed(3)}`);
      }

      // Q2: switch by src + seek to saved currentTime
      for (const file of ['a880.mp4', 'a440.mp4', 'a880.mp4']) {
        const saved = v.currentTime;
        const start = Date.now();
        v.src = URLS[file];
        const meta = await waitFor(v, 'loadedmetadata', 15000);
        v.currentTime = saved;
        const back = waitFor(v, 'playing', 15000);
        v.play();
        const played = await back;
        const total = Date.now() - start;
        await sleep(50);
        log(`Q2 src->${file} loadedmetadata=${meta}ms playing=${played === -1 ? 'TIMEOUT' : total + 'ms'} saved=${saved.toFixed(3)} now=${v.currentTime.toFixed(3)} err=${(v.currentTime - saved).toFixed(3)}s`);
        await sleep(3000);
      }

      // Q3: second player (audio-only) while p1 paused, then while p1 plays
      v.pause();
      log(`Q3 p1 paused=${v.paused} t=${v.currentTime.toFixed(3)}`);
      let a: Player;
      try {
        a = new AudioPlayer();
        await a.initialize();
        log('Q3 AudioPlayer initialized');
      } catch (e) {
        log(`Q3 AudioPlayer failed ${e}; trying VideoPlayer without surface`);
        a = new VideoPlayer();
        await a.initialize();
      }
      a.addEventListener('error', () => log(`Q3 p2 error ${JSON.stringify(a.error)}`));
      a.src = URLS['why.mp3'];
      const p2play = waitFor(a, 'playing', 10000);
      a.play();
      log(`Q3 p2 (p1 paused) playing after ${await p2play}ms`);
      await sleep(1000);
      log(`Q3 p2 t=${a.currentTime.toFixed(3)} p1 t=${v.currentTime.toFixed(3)} p1paused=${v.paused}`);
      log(`Q3 p2 ended after ${await waitFor(a, 'ended', 6000)}ms t=${a.currentTime.toFixed(3)}`);

      v.play();
      await sleep(500);
      a.currentTime = 0;
      const p2again = waitFor(a, 'playing', 10000);
      a.play();
      log(`Q3 p2 (p1 playing) playing after ${await p2again}ms`);
      for (let i = 0; i < 4; i++) {
        await sleep(500);
        log(`Q3 both p1 t=${v.currentTime.toFixed(3)} paused=${v.paused} | p2 t=${a.currentTime.toFixed(3)} paused=${a.paused}`);
      }
      log('DONE');
    };
    run().catch((e) => log(`FATAL ${e} ${e?.stack ?? ''}`));
  }, []);

  return (
    <View style={styles.root}>
      <KeplerVideoSurfaceView
        style={styles.video}
        onSurfaceViewCreated={(h: string) => surface.current(h)}
        onSurfaceViewDestroyed={() => {}}
      />
      <ScrollView style={styles.log}>
        {lines.map((l, i) => (
          <Text key={i} style={styles.text}>
            {l}
          </Text>
        ))}
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  root: {flex: 1, flexDirection: 'row', backgroundColor: '#000'},
  video: {width: 640, height: 360},
  log: {flex: 1, padding: 8},
  text: {color: '#0f0', fontSize: 12},
});
