import { StyleSheet, Text, View } from "react-native";

export function StateNotice({
  kind = "info",
  message,
}: {
  kind?: "info" | "error" | "warning";
  message: string;
}) {
  return (
    <View accessibilityRole={kind === "error" ? "alert" : "text"} style={[styles.notice, styles[kind]]}>
      <Text style={styles.text}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  notice: { borderRadius: 12, padding: 14, borderWidth: StyleSheet.hairlineWidth },
  info: { backgroundColor: "#eff6ff", borderColor: "#93c5fd" },
  warning: { backgroundColor: "#fffbeb", borderColor: "#fbbf24" },
  error: { backgroundColor: "#fef2f2", borderColor: "#fca5a5" },
  text: { color: "#1f2937", lineHeight: 20 },
});
