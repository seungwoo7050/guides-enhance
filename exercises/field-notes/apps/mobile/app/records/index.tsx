import { Link, useLocalSearchParams } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { useFieldNotes } from "../../src/application/FieldNotesRuntime";
import { ActionButton } from "../../src/components/ActionButton";
import { RecordListItem } from "../../src/components/RecordListItem";
import { Screen, commonStyles } from "../../src/components/Screen";
import { StateNotice } from "../../src/components/StateNotice";

function firstParameter(value: string | string[] | undefined): string | null {
  const first = Array.isArray(value) ? value[0] : value;
  return typeof first === "string" && first.length > 0 ? first : null;
}

export default function RecordsRoute() {
  const runtime = useFieldNotes();
  const params = useLocalSearchParams<{ navigationNotice?: string | string[] }>();
  const navigationNotice = firstParameter(params.navigationNotice);

  return (
    <Screen
      title="Field Notes"
      subtitle="Records are committed locally first and synchronized when an opportunity is available."
      actions={(
        <>
          <Link href="/records/new" asChild>
            <Pressable style={styles.primaryLink}>
              <Text style={styles.primaryLabel}>Create record</Text>
            </Pressable>
          </Link>
          <View style={styles.navigationRow}>
            <Link href="/sync" style={styles.link}>Sync status</Link>
            <Link href="/settings" style={styles.link}>Settings</Link>
          </View>
        </>
      )}
    >
      {!runtime.ready
        ? <StateNotice message="Opening the local database and reconciling attachment storage…" />
        : null}
      {navigationNotice ? (
        <StateNotice
          kind="warning"
          message={`The requested destination was not opened (${navigationNotice}).`}
        />
      ) : null}
      {runtime.error ? <StateNotice kind="error" message={runtime.error} /> : null}
      {runtime.ready && runtime.records.length === 0
        ? (
            <View style={commonStyles.card}>
              <Text style={styles.emptyTitle}>No records yet</Text>
              <Text style={commonStyles.muted}>
                Create a record while online or offline. The record and its outbox command are stored in one SQLite transaction.
              </Text>
            </View>
          )
        : null}
      <View style={commonStyles.gap}>
        {runtime.records.map((record) => <RecordListItem key={record.id} record={record} />)}
      </View>
      <ActionButton
        busy={runtime.busy}
        variant="secondary"
        onPress={() => void runtime.refresh()}
      >
        Refresh local state
      </ActionButton>
    </Screen>
  );
}

const styles = StyleSheet.create({
  emptyTitle: { color: "#111827", fontSize: 17, fontWeight: "700" },
  primaryLink: {
    alignItems: "center",
    justifyContent: "center",
    minHeight: 48,
    borderRadius: 12,
    backgroundColor: "#1d4ed8",
    paddingHorizontal: 18,
  },
  primaryLabel: { color: "white", fontSize: 16, fontWeight: "700" },
  navigationRow: { flexDirection: "row", justifyContent: "space-around", gap: 16 },
  link: { color: "#1d4ed8", fontSize: 15, fontWeight: "700" },
});
