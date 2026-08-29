import type { PropsWithChildren } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text } from "react-native";

export function ActionButton({
  children,
  onPress,
  disabled = false,
  busy = false,
  variant = "primary",
}: PropsWithChildren<{
  onPress(): void;
  disabled?: boolean;
  busy?: boolean;
  variant?: "primary" | "secondary" | "danger";
}>) {
  return (
    <Pressable
      accessibilityRole="button"
      disabled={disabled || busy}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        styles[variant],
        (disabled || busy) && styles.disabled,
        pressed && styles.pressed,
      ]}
    >
      {busy
        ? <ActivityIndicator color={variant === "secondary" ? "#1f2937" : "white"} />
        : <Text style={[styles.label, variant === "secondary" && styles.secondaryLabel]}>{children}</Text>}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    minHeight: 48,
    borderRadius: 12,
    paddingHorizontal: 18,
    alignItems: "center",
    justifyContent: "center",
  },
  primary: { backgroundColor: "#1d4ed8" },
  secondary: { backgroundColor: "#e5e7eb" },
  danger: { backgroundColor: "#b91c1c" },
  label: { color: "white", fontSize: 16, fontWeight: "700" },
  secondaryLabel: { color: "#1f2937" },
  disabled: { opacity: 0.45 },
  pressed: { opacity: 0.75 },
});
