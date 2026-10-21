import React, {useState} from 'react';
import {
  Pressable,
  StyleProp,
  StyleSheet,
  Text,
  View,
  ViewStyle,
} from 'react-native';
import {C, s} from '../theme';

interface Props {
  label: string;
  onPress: () => void;
  selected?: boolean; // toggled on / current: accent text + underline bar
  primary?: boolean; // the ONE primary action on a screen: accent fill
  hasTVPreferredFocus?: boolean;
  onFocusChange?: (focused: boolean) => void;
  // Cards pass their own content and box; `label` stays the log/accessibility name.
  children?: React.ReactNode;
  style?: StyleProp<ViewStyle>; // the visible box (inner)
  outerStyle?: StyleProp<ViewStyle>; // margins / sizing of the focus target
  card?: boolean; // cards use panelFocus while focused, buttons buttonFocus
}

// Focus ring (design/handoff README "Interactive states"): a dark gap then an accent ring, plus a lift.
// RN has no multi-shadow, so the ring is the outer Pressable's border and the gap is its padding.
export const FocusButton = ({
  label,
  onPress,
  selected,
  primary,
  hasTVPreferredFocus,
  onFocusChange,
  children,
  style,
  outerStyle,
  card,
}: Props) => {
  const [focused, setFocused] = useState(false);
  return (
    <Pressable
      onPress={() => {
        console.warn(`YOC: press ${label}`);
        onPress();
      }}
      onFocus={() => {
        console.warn(`YOC: focus ${label}`);
        setFocused(true);
        onFocusChange?.(true);
      }}
      onBlur={() => {
        setFocused(false);
        onFocusChange?.(false);
      }}
      hasTVPreferredFocus={hasTVPreferredFocus}
      accessibilityRole="button"
      accessibilityLabel={label}
      style={[
        styles.ring,
        {borderRadius: s(card ? 30 : 24)},
        outerStyle,
        focused && styles.ringOn,
      ]}>
      <View
        style={[
          styles.box,
          style,
          primary && styles.primary,
          selected && !primary && styles.selected,
          focused &&
            !primary && {backgroundColor: card ? C.panelFocus : C.buttonFocus},
        ]}>
        {children ?? (
          <Text
            style={[
              styles.label,
              primary && styles.primaryLabel,
              selected && !primary && styles.selectedLabel,
            ]}>
            {label}
          </Text>
        )}
      </View>
    </Pressable>
  );
};

const styles = StyleSheet.create({
  ring: {
    borderWidth: s(8),
    borderColor: 'transparent',
    padding: s(3),
    marginRight: s(4),
    marginBottom: s(4),
  },
  ringOn: {
    borderColor: C.accent,
    transform: [{translateY: s(-4)}, {scale: 1.04}],
    zIndex: 10,
  },
  box: {
    minHeight: s(72),
    justifyContent: 'center',
    paddingHorizontal: s(28),
    borderRadius: s(14),
    borderWidth: 1,
    borderColor: C.lineStrong,
    backgroundColor: C.panel2,
  },
  primary: {backgroundColor: C.accent, borderColor: C.accent},
  selected: {borderBottomWidth: s(5), borderBottomColor: C.accent},
  label: {color: C.text, fontSize: s(26), fontWeight: '700'},
  primaryLabel: {color: C.accentInk},
  selectedLabel: {color: C.accent},
});
