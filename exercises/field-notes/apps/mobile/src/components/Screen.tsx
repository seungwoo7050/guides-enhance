import type { PropsWithChildren, ReactNode } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

export function Screen({
  title,
  subtitle,
  children,
  actions,
}: PropsWithChildren<{
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}>) {
  return (
    <SafeAreaView style={styles.safe} edges={["bottom"]}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <View style={styles.header}>
          <Text accessibilityRole="header" style={styles.title}>{title}</Text>
          {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
        </View>
        {children}
        {actions ? <View style={styles.actions}>{actions}</View> : null}
      </ScrollView>
    </SafeAreaView>
  );
}

export const commonStyles = StyleSheet.create({
  card: {
    backgroundColor: "white",
    borderColor: "#d1d5db",
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: 14,
    padding: 16,
    gap: 10,
  },
  label: { color: "#374151", fontSize: 13, fontWeight: "700" },
  muted: { color: "#6b7280", fontSize: 14 },
  row: { flexDirection: "row", alignItems: "center", gap: 10 },
  gap: { gap: 14 },
});

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#f8fafc" },
  content: { padding: 18, gap: 16, paddingBottom: 40 },
  header: { gap: 4 },
  title: { fontSize: 28, fontWeight: "800", color: "#111827" },
  subtitle: { color: "#6b7280", fontSize: 15, lineHeight: 22 },
  actions: { gap: 10, marginTop: 6 },
});
