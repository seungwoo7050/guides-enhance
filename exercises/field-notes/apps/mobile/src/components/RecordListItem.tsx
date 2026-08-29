import type { FieldRecord } from "@field-notes/core";
import { Link } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";

export function RecordListItem({ record }: { record: FieldRecord }) {
  return (
    <Link href={`/records/${record.id}` as never} asChild>
      <Pressable style={({ pressed }) => [styles.card, pressed && styles.pressed]}>
        <View style={styles.row}>
          <Text numberOfLines={1} style={styles.title}>{record.title}</Text>
          <Text style={styles.state}>{record.syncState}</Text>
        </View>
        <Text numberOfLines={2} style={styles.notes}>{record.notes || "No notes"}</Text>
        <Text style={styles.meta}>{record.status} · {new Date(record.observedAt).toLocaleString()}</Text>
      </Pressable>
    </Link>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "white",
    borderRadius: 14,
    padding: 16,
    gap: 8,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: "#d1d5db",
  },
  pressed: { opacity: 0.7 },
  row: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12 },
  title: { color: "#111827", fontSize: 17, fontWeight: "700", flex: 1 },
  state: { color: "#1d4ed8", fontSize: 12, fontWeight: "700" },
  notes: { color: "#4b5563", lineHeight: 20 },
  meta: { color: "#6b7280", fontSize: 12 },
});
