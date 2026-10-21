import React from 'react';
import {Text, View} from 'react-native';
import Svg, {
  Circle,
  ClipPath,
  Defs,
  G,
  Path,
  Rect,
  Text as SvgText,
} from '@amazon-devices/react-native-svg';
import {C, PERSONA_TINT, PersonaKey} from '../theme';

// design/handoff/YOC Mark.dc.html: a ball with seams and a speech-bubble tail.
export const Mark = ({size, ink = false}: {size: number; ink?: boolean}) => {
  const fill = ink ? C.accentInk : C.accent;
  const seam = ink ? C.accent : C.accentInk;
  return (
    <Svg width={size} height={size} viewBox="0 0 100 100">
      <Defs>
        <ClipPath id="yocBall">
          <Circle cx="54" cy="46" r="36" />
        </ClipPath>
      </Defs>
      <Circle cx="54" cy="46" r="36" fill={fill} />
      <Path d="M27 70 L14 92 L44 80 Z" fill={fill} />
      <G
        clipPath="url(#yocBall)"
        fill="none"
        stroke={seam}
        strokeWidth={4.5}
        strokeLinecap="round">
        <Path d="M18 46 H90" />
        <Path d="M54 10 V82" />
        <Path d="M30 17 C42 30 42 62 30 75" />
        <Path d="M78 17 C66 30 66 62 78 75" />
      </G>
    </Svg>
  );
};

// "Your Own " 400 + "Commentator" 800.
export const Wordmark = ({size}: {size: number}) => (
  <Text style={{color: C.text, fontSize: size}}>
    Your Own <Text style={{fontWeight: '800'}}>Commentator</Text>
  </Text>
);

const GLYPH: Record<PersonaKey, React.ReactNode> = {
  rookie: (
    <Path d="M32 18 C26 14 18 13 9 14 V48 C18 47 26 48 32 52 C38 48 46 47 55 48 V14 C46 13 38 14 32 18 Z M32 18 V52" />
  ),
  kid: (
    <>
      <Path d="M32 7 L39.5 23.5 L57 25 L43.5 36.5 L47.5 54 L32 45 L16.5 54 L20.5 36.5 L7 25 L24.5 23.5 Z" />
      <Path d="M27 31 V33 M37 31 V33" />
    </>
  ),
  booth: (
    <>
      <Rect x="11" y="9" width="13" height="22" rx="6.5" />
      <Rect x="40" y="9" width="13" height="22" rx="6.5" />
      <Path d="M6 24 a11.5 11.5 0 0 0 23 0 M35 24 a11.5 11.5 0 0 0 23 0 M17.5 36 V50 M46.5 36 V50 M10 54 H25 M39 54 H54" />
    </>
  ),
  fantasy: <Path d="M9 52 H55 M12 42 L24 31 L34 37 L51 18 M41 18 H51 V28" />,
  novato: (
    <>
      <Path d="M13 12 H51 a5 5 0 0 1 5 5 V39 a5 5 0 0 1 -5 5 H29 L18 54 V44 H13 a5 5 0 0 1 -5 -5 V17 a5 5 0 0 1 5 -5 Z" />
      <SvgText
        x="32"
        y="36"
        textAnchor="middle"
        fontSize="24"
        fontWeight="800"
        fill={C.text}
        stroke="none">
        Ñ
      </SvgText>
    </>
  ),
  hindi: (
    <>
      <SvgText
        x="32"
        y="46"
        textAnchor="middle"
        fontSize="40"
        fontWeight="700"
        fill={C.text}
        stroke="none">
        न
      </SvgText>
      <Path d="M8 12 H56" />
    </>
  ),
  mandarin: (
    <>
      <SvgText
        x="32"
        y="46"
        textAnchor="middle"
        fontSize="38"
        fontWeight="700"
        fill={C.text}
        stroke="none">
        新
      </SvgText>
      <Circle cx="32" cy="33" r="27" strokeWidth={3} />
    </>
  ),
};

// design/handoff/YOC Persona.dc.html: tinted tile, 22% radius, hairline edge, 62% glyph.
export const PersonaIcon = ({
  persona,
  size,
  dim = false,
}: {
  persona: PersonaKey;
  size: number;
  dim?: boolean;
}) => (
  <View
    style={{
      width: size,
      height: size,
      borderRadius: size * 0.22,
      backgroundColor: PERSONA_TINT[persona],
      borderWidth: 1,
      borderColor: C.glassEdge,
      alignItems: 'center',
      justifyContent: 'center',
      opacity: dim ? 0.5 : 1,
    }}>
    <Svg
      width={size * 0.62}
      height={size * 0.62}
      viewBox="0 0 64 64"
      fill="none"
      stroke={C.text}
      strokeWidth={4}
      strokeLinecap="round"
      strokeLinejoin="round">
      {GLYPH[persona]}
    </Svg>
  </View>
);
