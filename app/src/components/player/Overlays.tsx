// Presentational pieces of the Player overlays (design/handoff 03 TV Player + YOC Score Bug / Minimap).
import React, {useEffect, useRef} from 'react';
import {Animated, StyleSheet, Text, View} from 'react-native';
import Svg, {Circle, Path, Rect} from '@amazon-devices/react-native-svg';
import {PersonaIcon} from '../Brand';
import {C, PersonaKey, SAFE, T, eyebrow, s, team} from '../../theme';

export const glass = {
  backgroundColor: C.glass,
  borderWidth: 1,
  borderColor: C.glassEdge,
};

// ▶ drawn with borders (a text glyph can render as an emoji).
export const Play = ({color = C.text}: {color?: string}) => (
  <View
    style={{
      width: 0,
      height: 0,
      borderLeftWidth: s(18),
      borderLeftColor: color,
      borderTopWidth: s(12),
      borderTopColor: 'transparent',
      borderBottomWidth: s(12),
      borderBottomColor: 'transparent',
    }}
  />
);

// Team colour chip: "PINK #23" (minors: colour + jersey only).
export const TeamChip = ({name, text, h = 38}: {name: string; text: string; h?: number}) => (
  <View style={[st.teamChip, {height: s(h), backgroundColor: team(name).bg}]}>
    <Text style={[st.teamChipText, {color: team(name).ink}]}>{text}</Text>
  </View>
);

export const ScoreBug = ({
  score,
  flash,
}: {
  score: Record<string, number>;
  flash: {team: string; pts: number} | null;
}) => {
  const teams = Object.entries(score);
  return (
    <View style={st.bugRow}>
      <View style={[st.bug, glass]}>
        {teams.map(([k, v], i) => {
          const name = (
            <Text key="n" style={[st.bugName, {color: team(k).ink}]}>
              {k.toUpperCase()}
            </Text>
          );
          const pts = (
            <Text key="p" style={[st.bugScore, {color: team(k).ink}]}>
              {v}
            </Text>
          );
          return (
            <View key={k} style={[st.bugTeam, {backgroundColor: team(k).bg}]}>
              {i === 0 ? [name, pts] : [pts, name]}
              {flash?.team === k && <View style={st.bugBar} />}
            </View>
          );
        })}
      </View>
      {flash && flash.pts > 0 && (
        <View style={st.flash}>
          <Text style={st.flashText}>
            +{flash.pts} {flash.team.toUpperCase()}
          </Text>
        </View>
      )}
    </View>
  );
};

const Phone = ({w = 22, h = 36}: {w?: number; h?: number}) => (
  <View style={[st.phone, {width: s(w), height: s(h)}]} />
);

export const CodeBadge = ({code}: {code: string}) => (
  <View style={[st.badge, glass]}>
    <Phone />
    <Text style={st.badgeText}>Ask on your phone</Text>
    <View style={st.codeChip}>
      <Text style={st.codeText}>{code}</Text>
    </View>
  </View>
);

export const PhoneRow = ({code}: {code: string}) => (
  <View style={st.phoneRow}>
    <Phone w={30} h={48} />
    <Text style={st.soft}>
      Or hold to ask on your phone — code <Text style={st.codeInline}>{code}</Text>
    </Text>
  </View>
);

export const PausedPill = () => (
  <View style={[st.paused, glass]}>
    <View style={st.pauseBar} />
    <View style={st.pauseBar} />
    <Text style={st.pausedText}>PAUSED</Text>
  </View>
);

export const Caption = ({
  persona,
  role,
  speaker,
  text,
}: {
  persona: PersonaKey;
  role?: 'pbp' | 'analyst';
  speaker: string;
  text: string;
}) => (
  <View style={[st.caption, glass]}>
    <PersonaIcon persona={persona} size={s(72)} />
    <View style={st.flex}>
      <View style={st.captionHead}>
        {role === 'pbp' && (
          <View style={[st.role, st.rolePbp]}>
            <Text style={[st.roleText, {color: C.accent}]}>PLAY-BY-PLAY</Text>
          </View>
        )}
        {role === 'analyst' && (
          <View style={[st.role, {backgroundColor: C.text}]}>
            <Text style={[st.roleText, {color: C.accentInk}]}>ANALYST</Text>
          </View>
        )}
        <Text style={st.muted}>{speaker}</Text>
      </View>
      <Text style={st.captionText}>{text}</Text>
    </View>
  </View>
);

// YOC Minimap: 320x180 viewBox, court 300x160 at (10,10); frames are metres on a 28.65 x 15.24 court.
const COURT = {w: 28.65, h: 15.24};
const LINE = 'rgba(230,237,243,.55)';
const px = (x: number) => 10 + (x / COURT.w) * 300;
const py = (y: number) => 10 + (y / COURT.h) * 160;
export const MiniMap = ({
  frame,
}: {
  frame: {
    players: {id: number; team: string; x: number; y: number}[];
    ball: {x: number; y: number} | null;
  };
}) => (
  <View style={[st.map, glass]}>
    <View style={st.mapHead}>
      <Text style={eyebrow}>MAP</Text>
      <View style={st.legend}>
        <View style={st.legendBall} />
        <Text style={st.legendText}>ball</Text>
      </View>
    </View>
    <Svg width={s(320)} height={s(180)} viewBox="0 0 320 180">
      <Rect x="10" y="10" width="300" height="160" rx="6" fill="rgba(193,138,81,.16)" stroke={LINE} strokeWidth={2} />
      <Path d="M160 10 V170" stroke={LINE} strokeWidth={2} />
      <Circle cx="160" cy="90" r="22" fill="none" stroke={LINE} strokeWidth={2} />
      <Rect x="10" y="62" width="54" height="56" fill="none" stroke={LINE} strokeWidth={2} />
      <Rect x="256" y="62" width="54" height="56" fill="none" stroke={LINE} strokeWidth={2} />
      <Path d="M64 62 a28 28 0 0 1 0 56 M256 62 a28 28 0 0 0 0 56" fill="none" stroke={LINE} strokeWidth={2} />
      <Path d="M10 22 Q 110 90 10 158 M310 22 Q 210 90 310 158" fill="none" stroke="rgba(230,237,243,.35)" strokeWidth={2} />
      {frame.players.map((p) => (
        <Circle key={p.id} cx={px(p.x)} cy={py(p.y)} r="8" fill={team(p.team).bg} stroke="#ffffff" strokeWidth={2} />
      ))}
      {frame.ball && (
        <Circle cx={px(frame.ball.x)} cy={py(frame.ball.y)} r="7" fill={C.accent} stroke={C.bg} strokeWidth={2.5} />
      )}
    </Svg>
  </View>
);

// 3b: the bar shrinks over the card's on-screen time (left = 1 → 0).
export const RuleCard = ({title, body, left}: {title: string; body: string; left: number}) => (
  <View style={[st.rule, glass]}>
    <View style={st.ruleBody}>
      <Text style={[eyebrow, {color: C.accent}]}>RULE</Text>
      <Text style={st.ruleTitle}>{title}</Text>
      <Text style={st.ruleText}>{body}</Text>
    </View>
    <View style={st.track}>
      <View style={[st.fill, {width: `${Math.max(0, Math.min(1, left)) * 100}%`}]} />
    </View>
  </View>
);

// 3d: old persona dimmed under the new one; the bar fills over the ≈1.5 s a switch takes.
export const SwitchCard = ({from, to, name}: {from: PersonaKey; to: PersonaKey; name: string}) => {
  const p = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    Animated.timing(p, {toValue: 1, duration: 1500, useNativeDriver: true}).start();
  }, [p]);
  return (
    <View style={[st.switch, glass]}>
      <View style={st.switchBody}>
        <View style={st.switchIcons}>
          <View style={st.oldIcon}>
            <PersonaIcon persona={from} size={s(72)} dim />
          </View>
          <View style={st.newIcon}>
            <PersonaIcon persona={to} size={s(84)} />
          </View>
        </View>
        <Text style={st.switchText}>Switching to {name}…</Text>
      </View>
      <View style={[st.track, {height: s(8)}]}>
        <Animated.View
          style={[
            st.fill,
            {
              height: s(8),
              width: '100%',
              transformOrigin: 'left',
              transform: [{scaleX: p.interpolate({inputRange: [0, 1], outputRange: [0, 0.9]})}],
            },
          ]}
        />
      </View>
    </View>
  );
};

// 3e / 3f top-centre tag: REPLAY (accent fill) or HIGHLIGHTS (outlined).
export const ModeTag = ({kind, detail}: {kind: 'replay' | 'highlights'; detail?: string | null}) => {
  const replay = kind === 'replay';
  return (
    <View style={st.tagWrap} pointerEvents="none">
      <View style={[st.tag, replay ? st.tagReplay : st.tagReel]}>
        <Text style={[st.tagText, {color: replay ? C.accentInk : C.accent}]}>
          {replay ? '↺ REPLAY' : '★ HIGHLIGHTS'}
        </Text>
        {detail ? <Text style={[st.tagDetail, {color: replay ? C.accentInk : C.text}]}>{detail}</Text> : null}
      </View>
    </View>
  );
};

export const st = StyleSheet.create({
  flex: {flex: 1},
  muted: {...T.body, color: C.muted},
  soft: {...T.body, color: C.textSoft, flexShrink: 1},
  teamChip: {justifyContent: 'center', paddingHorizontal: s(10), borderRadius: s(8)},
  teamChipText: {fontSize: s(24), fontWeight: '800'},
  bugRow: {position: 'absolute', left: SAFE.x, top: SAFE.y, flexDirection: 'row', alignItems: 'center'},
  bug: {flexDirection: 'row', height: s(76), borderRadius: s(16), overflow: 'hidden'},
  bugTeam: {flexDirection: 'row', alignItems: 'center', paddingHorizontal: s(22)},
  bugName: {fontSize: s(24), fontWeight: '700', letterSpacing: s(2.9), marginHorizontal: s(9)},
  bugScore: {...T.score, marginHorizontal: s(9)},
  bugBar: {position: 'absolute', left: 0, right: 0, bottom: 0, height: s(6), backgroundColor: C.accent},
  flash: {height: s(56), marginLeft: s(12), paddingHorizontal: s(20), borderRadius: s(28), backgroundColor: C.accent, justifyContent: 'center'},
  flashText: {fontSize: s(26), fontWeight: '800', color: C.accentInk},
  phone: {borderWidth: s(3), borderColor: C.text, borderRadius: s(6)},
  badge: {
    position: 'absolute',
    right: SAFE.x,
    top: SAFE.y,
    height: s(76),
    paddingLeft: s(24),
    paddingRight: s(12),
    borderRadius: s(16),
    flexDirection: 'row',
    alignItems: 'center',
  },
  badgeText: {fontSize: s(24), fontWeight: '700', color: C.text, marginHorizontal: s(16)},
  codeChip: {height: s(56), paddingHorizontal: s(18), borderRadius: s(10), backgroundColor: C.accent, justifyContent: 'center'},
  codeText: {fontSize: s(32), fontWeight: '800', letterSpacing: s(5.8), color: C.accentInk},
  codeInline: {color: C.accent, fontWeight: '800', letterSpacing: s(2.9)},
  phoneRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: s(20),
    marginTop: s(8),
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: C.line,
  },
  paused: {
    position: 'absolute',
    left: SAFE.x,
    top: s(154),
    height: s(56),
    paddingHorizontal: s(20),
    borderRadius: s(28),
    flexDirection: 'row',
    alignItems: 'center',
  },
  pauseBar: {width: s(7), height: s(22), backgroundColor: C.text, marginRight: s(5)},
  pausedText: {fontSize: s(24), fontWeight: '800', letterSpacing: s(3.4), color: C.text, marginLeft: s(7)},
  caption: {
    position: 'absolute',
    left: SAFE.x,
    bottom: s(166),
    width: s(1080),
    paddingVertical: s(24),
    paddingHorizontal: s(28),
    borderRadius: s(24),
    flexDirection: 'row',
    gap: s(24),
  },
  captionHead: {flexDirection: 'row', alignItems: 'center', gap: s(14), marginBottom: s(10)},
  role: {height: s(36), paddingHorizontal: s(12), borderRadius: s(8), justifyContent: 'center'},
  rolePbp: {borderWidth: s(2), borderColor: C.accent},
  roleText: {fontSize: s(24), fontWeight: '800', letterSpacing: s(2.9)},
  captionText: {...T.caption, color: C.text},
  map: {
    position: 'absolute',
    right: SAFE.x,
    bottom: s(166),
    width: s(360),
    paddingTop: s(16),
    paddingHorizontal: s(20),
    paddingBottom: s(20),
    borderRadius: s(24),
  },
  mapHead: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: s(10)},
  legend: {flexDirection: 'row', alignItems: 'center', gap: s(8)},
  legendBall: {width: s(14), height: s(14), borderRadius: s(7), backgroundColor: C.accent, borderWidth: s(2), borderColor: C.bg},
  legendText: {fontSize: s(24), fontWeight: '700', color: C.text},
  rule: {position: 'absolute', left: SAFE.x, top: s(162), width: s(600), borderRadius: s(24), overflow: 'hidden'},
  ruleBody: {paddingTop: s(24), paddingHorizontal: s(28), paddingBottom: s(28), gap: s(12)},
  ruleTitle: {fontSize: s(36), lineHeight: s(44), fontWeight: '800', color: C.text},
  ruleText: {fontSize: s(26), lineHeight: s(38), color: C.textSoft},
  track: {height: s(6), backgroundColor: C.line},
  fill: {height: s(6), backgroundColor: C.accent},
  switch: {position: 'absolute', left: SAFE.x, bottom: s(166), width: s(860), borderRadius: s(24), overflow: 'hidden'},
  switchBody: {paddingVertical: s(28), paddingHorizontal: s(32), flexDirection: 'row', alignItems: 'center', gap: s(28)},
  switchIcons: {width: s(112), height: s(112)},
  oldIcon: {position: 'absolute', left: 0, top: 0},
  newIcon: {position: 'absolute', right: 0, bottom: 0, borderWidth: s(4), borderColor: '#090e14', borderRadius: s(22)},
  switchText: {...T.h2, color: C.text, flexShrink: 1},
  tagWrap: {position: 'absolute', top: SAFE.y, left: 0, right: 0, alignItems: 'center'},
  tag: {height: s(76), paddingHorizontal: s(28), borderRadius: s(16), flexDirection: 'row', alignItems: 'center', gap: s(16)},
  tagReplay: {backgroundColor: C.accent},
  tagReel: {backgroundColor: C.glass, borderWidth: s(3), borderColor: C.accent},
  tagText: {fontSize: s(30), fontWeight: '800', letterSpacing: s(4.8)},
  tagDetail: {fontSize: s(24), fontWeight: '700', letterSpacing: s(1)},
});
