import React, {useState} from 'react';
import {Pressable, StyleSheet, Text} from 'react-native';

interface Props {
  label: string;
  onPress: () => void;
  selected?: boolean;
  hasTVPreferredFocus?: boolean;
}

export const FocusButton = ({
  label,
  onPress,
  selected,
  hasTVPreferredFocus,
}: Props) => {
  const [focused, setFocused] = useState(false);
  return (
    <Pressable
      onPress={onPress}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
      hasTVPreferredFocus={hasTVPreferredFocus}
      accessibilityRole="button"
      accessibilityLabel={label}
      style={[
        styles.button,
        selected && styles.selected,
        focused && styles.focused,
      ]}>
      <Text style={styles.label}>{label}</Text>
    </Pressable>
  );
};

const styles = StyleSheet.create({
  button: {
    paddingVertical: 18,
    paddingHorizontal: 36,
    marginRight: 24,
    marginBottom: 20,
    borderRadius: 14,
    borderWidth: 5,
    borderColor: 'transparent',
    backgroundColor: 'rgba(20,24,36,0.85)',
  },
  selected: {backgroundColor: '#2446b8'},
  focused: {borderColor: '#FFD400', transform: [{scale: 1.08}]},
  label: {color: '#FFFFFF', fontSize: 34, fontWeight: '600'},
});
