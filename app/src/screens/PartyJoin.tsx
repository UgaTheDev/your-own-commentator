import React, {useEffect} from 'react';
import {BackHandler, StyleSheet, Text, View} from 'react-native';
import {Mark, Wordmark} from '../components/Brand';
import {FocusButton} from '../components/FocusButton';
import {Member} from '../party';
import {C, SAFE, T, eyebrow, s} from '../theme';

interface Props {
  code: string;
  members: Member[];
  heading: string; // "PINK VS BLUE"
  onStart: () => void;
  onSolo: () => void;
  onBack: () => void;
}

// design/handoff "04 Why + Watch Party" 4d. Tiles are 180 wide for 4 characters; narrower for longer codes
// so a 6-character code still fits left of the room panel.
const LEFT_W = 1000;
const GAP = 20;

export const PartyJoin = ({
  code,
  members,
  heading,
  onStart,
  onSolo,
  onBack,
}: Props) => {
  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', () => {
      console.warn('YOC: back party join');
      onBack();
      return true;
    });
    return () => sub.remove();
  }, [onBack]);

  const chars = code.split('');
  const tileW = Math.min(
    180,
    (LEFT_W - GAP * (chars.length - 1)) / chars.length,
  );
  return (
    <View style={styles.root}>
      <View style={[styles.ring, styles.ringBig]} />
      <View style={[styles.ring, styles.ringSmall]} />
      <View style={styles.header}>
        <Mark size={s(56)} />
        <Wordmark size={s(30)} />
      </View>

      <View style={styles.left}>
        <Text style={[eyebrow, styles.accent]}>WATCH PARTY · {heading}</Text>
        <Text style={styles.h}>Join on your phone</Text>
        <Text style={styles.body}>
          Open the watch party page on your phone and enter this code. Everyone
          calls the next basket.
        </Text>
        <View style={styles.tiles}>
          {chars.map((ch, i) => (
            <View key={i} style={[styles.tile, {width: s(tileW)}]}>
              <Text
                style={[
                  styles.tileText,
                  {fontSize: s(Math.min(140, tileW * 0.8))},
                ]}>
                {ch}
              </Text>
            </View>
          ))}
        </View>
        <View style={styles.buttons}>
          <FocusButton
            label="Start the party"
            primary
            hasTVPreferredFocus
            onPress={onStart}
            style={[styles.btn, styles.btnPrimary]}
            outerStyle={styles.btnOuter}>
            <Text style={[styles.btnText, styles.btnTextPrimary]}>
              Start the party
            </Text>
          </FocusButton>
          <FocusButton
            label="Watch solo"
            onPress={onSolo}
            style={styles.btn}
            outerStyle={styles.btnOuter}>
            <Text style={styles.btnText}>Watch solo</Text>
          </FocusButton>
        </View>
      </View>

      <View style={styles.room}>
        <View style={styles.roomHead}>
          <Text style={eyebrow}>IN THE ROOM</Text>
          <Text style={styles.count}>{members.length}</Text>
        </View>
        {members.length === 0 && <Text style={styles.empty}>Connecting…</Text>}
        {members.map((m, i) => (
          <View key={`${m.name}-${i}`} style={styles.row}>
            <View style={[styles.disc, i === 0 && styles.discFirst]}>
              <Text style={styles.discText}>{i + 1}</Text>
            </View>
            <Text style={styles.name} numberOfLines={1}>
              {m.name}
            </Text>
            <Text style={styles.points}>
              {m.points} {m.points === 1 ? 'pt' : 'pts'}
            </Text>
          </View>
        ))}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  root: {flex: 1, backgroundColor: C.bg, overflow: 'hidden'},
  ring: {position: 'absolute', borderRadius: 9999, borderWidth: s(3)},
  ringBig: {
    right: s(-300),
    top: s(-200),
    width: s(1200),
    height: s(1200),
    borderColor: 'rgba(255,212,0,0.10)',
  },
  ringSmall: {
    right: s(100),
    top: s(140),
    width: s(800),
    height: s(800),
    borderColor: 'rgba(255,212,0,0.07)',
  },
  header: {
    position: 'absolute',
    left: SAFE.x,
    top: SAFE.y,
    height: s(64),
    flexDirection: 'row',
    alignItems: 'center',
    gap: s(16),
  },
  left: {
    position: 'absolute',
    left: SAFE.x,
    top: s(210),
    width: s(LEFT_W),
    gap: s(28),
  },
  accent: {color: C.accent},
  h: {
    color: C.text,
    fontSize: s(72),
    lineHeight: s(80),
    fontWeight: '800',
    letterSpacing: s(-1.8),
  },
  body: {...T.bodyL, color: C.textSoft},
  tiles: {flexDirection: 'row', gap: s(GAP), marginTop: s(16)},
  tile: {
    height: s(220),
    borderRadius: s(24),
    backgroundColor: C.panel,
    borderWidth: s(2),
    borderColor: C.lineStrong,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tileText: {color: C.accent, fontWeight: '800'},
  // FocusButton's ring is 11 px outside the box; pull the row back so the boxes sit on the grid.
  buttons: {flexDirection: 'row', marginTop: s(24 - 11), marginLeft: s(-11)},
  btnOuter: {marginRight: s(20 - 22)},
  btn: {height: s(88), borderRadius: s(14), paddingHorizontal: s(32)},
  btnPrimary: {paddingHorizontal: s(40)},
  btnText: {color: C.text, fontSize: s(30), fontWeight: '700'},
  btnTextPrimary: {color: C.accentInk, fontWeight: '800'},
  room: {
    position: 'absolute',
    right: SAFE.x,
    top: s(210),
    width: s(560),
    padding: s(40),
    borderRadius: s(28),
    backgroundColor: C.panel,
    borderWidth: 1,
    borderColor: C.line,
    gap: s(20),
  },
  roomHead: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
  },
  count: {color: C.text, fontSize: s(40), fontWeight: '800'},
  empty: {color: C.muted, fontSize: s(24)},
  row: {
    height: s(80),
    paddingHorizontal: s(20),
    borderRadius: s(16),
    backgroundColor: C.panel2,
    flexDirection: 'row',
    alignItems: 'center',
    gap: s(16),
  },
  disc: {
    width: s(44),
    height: s(44),
    borderRadius: s(22),
    backgroundColor: C.text,
    alignItems: 'center',
    justifyContent: 'center',
  },
  discFirst: {backgroundColor: C.accent},
  discText: {color: C.accentInk, fontSize: s(24), fontWeight: '800'},
  name: {color: C.text, fontSize: s(28), fontWeight: '700', flex: 1},
  points: {color: C.accent, fontSize: s(24), fontWeight: '700'},
});
