import React, {useState} from 'react';
import {Pressable, StyleProp, StyleSheet, Text, ViewStyle} from 'react-native';
import {C, s} from '../theme';

interface Props {
  label: string;
  onPress: () => void;
  selected?: boolean;
  hasTVPreferredFocus?: boolean;
  onFocusChange?: (focused: boolean) => void;
  // Cards (Home) pass their own content and box; `label` stays the log/accessibility name.
  children?: React.ReactNode;
  style?: StyleProp<ViewStyle>;
}

export const FocusButton = ({
  label,
  onPress,
  selected,
  hasTVPreferredFocus,
  onFocusChange,
  children,
  style,
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
        styles.button,
        style,
        selected && styles.selected,
        focused && styles.focused,
      ]}>
      {children ?? (
        <Text style={[styles.label, selected && styles.labelSelected]}>
          {label}
        </Text>
      )}
    </Pressable>
  );
};

const styles = StyleSheet.create({
  button: {
    paddingVertical: s(14),
    paddingHorizontal: s(28),
    marginRight: s(16),
    marginBottom: s(16),
    borderRadius: 999,
    borderWidth: 3,
    borderColor: C.line,
    backgroundColor: C.glass,
  },
  selected: {borderColor: C.lineStrong, backgroundColor: C.panel2},
  focused: {
    borderColor: C.accent,
    backgroundColor: '#1d2116',
    transform: [{scale: 1.06}],
  },
  label: {color: C.text, fontSize: s(28), fontWeight: '600'},
  labelSelected: {color: C.accent},
});
