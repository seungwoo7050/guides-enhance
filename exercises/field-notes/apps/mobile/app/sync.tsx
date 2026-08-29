import type { RecordConflict, RecordPayload } from "@field-notes/core";
import { StyleSheet, Text, View } from "react-native";
import { useFieldNotes } from "../src/application/FieldNotesRuntime";
import { ActionButton } from "../src/components/ActionButton";
import { Screen, commonStyles } from "../src/components/Screen";
import { StateNotice } from "../src/components/StateNotice";

function mergePayload(conflict: RecordConflict): RecordPayload | null {
  const local = conflict.local.payload;
  const remote = conflict.remote?.payload ?? null;
  if (!local || !remote) return null;
  return {
    ...local,
    notes: [local.notes, remote.notes]
      .filter((value, index, values) => value.length > 0 && values.indexOf(value) === index)
      .join("\n\n--- Remote version ---\n\n"),
    location: local.location ?? remote.location,
  };
}

export default function SyncRoute() {
  const runtime = useFieldNotes();
  const unresolved = runtime.conflicts.filter((conflict) => !conflict.resolution);
  const activeOutbox = runtime.outbox.filter(
    (entry) => entry.state !== "applied" && entry.state !== "superseded",
  );

  return (
    <Screen
      title="Sync status"
      subtitle="A bounded worker claims durable commands, validates each response, and checkpoints exactly one outcome per attempt."
      actions={(
        <>
          <ActionButton busy={runtime.busy} onPress={() => void runtime.syncNow()}>Run sync now</ActionButton>
          <ActionButton
            busy={runtime.busy}
            variant="secondary"
            onPress={() => void runtime.resumeAuthentication()}
          >
            Resume after authentication
          </ActionButton>
        </>
      )}
    >
      {runtime.error ? <StateNotice kind="error" message={runtime.error} /> : null}
      <View style={commonStyles.card}>
        <Text style={commonStyles.label}>Queue</Text>
        <Text style={styles.metric}>{activeOutbox.length} active command(s)</Text>
        <Text style={commonStyles.muted}>{runtime.outbox.length} total durable command(s)</Text>
      </View>
      <View style={commonStyles.gap}>
        {activeOutbox.map((entry) => (
          <View key={entry.commandId} style={commonStyles.card}>
            <View style={styles.row}>
              <Text numberOfLines={1} style={styles.title}>{entry.operation} · {entry.recordId}</Text>
              <Text style={styles.state}>{entry.state}</Text>
            </View>
            <Text style={commonStyles.muted}>
              attempt {entry.attemptCount} · local revision {entry.localRevision} · base {entry.baseVersion ?? "none"}
            </Text>
            {entry.lastError ? <Text style={styles.error}>{entry.lastError}</Text> : null}
          </View>
        ))}
      </View>
      <View style={commonStyles.gap}>
        <Text style={styles.sectionTitle}>Conflicts</Text>
        {unresolved.length === 0
          ? <StateNotice message="No unresolved conflicts" />
          : unresolved.map((conflict) => {
              const merged = mergePayload(conflict);
              return (
                <View key={conflict.conflictId} style={commonStyles.card}>
                  <Text style={styles.title}>Record {conflict.recordId}</Text>
                  <Text style={commonStyles.muted}>
                    Local revision {conflict.local.localRevision} conflicts with remote version {conflict.remote?.version ?? "missing"}.
                  </Text>
                  <ActionButton
                    busy={runtime.busy}
                    variant="secondary"
                    onPress={() => void runtime.resolveConflict({
                      conflictId: conflict.conflictId,
                      kind: "remote",
                    })}
                  >
                    Accept remote state
                  </ActionButton>
                  <ActionButton
                    busy={runtime.busy}
                    variant="secondary"
                    onPress={() => void runtime.resolveConflict({
                      conflictId: conflict.conflictId,
                      kind: "local",
                    })}
                  >
                    Keep local state
                  </ActionButton>
                  {merged ? (
                    <ActionButton
                      busy={runtime.busy}
                      onPress={() => void runtime.resolveConflict({
                        conflictId: conflict.conflictId,
                        kind: "merge",
                        payload: merged,
                      })}
                    >
                      Merge notes and retry
                    </ActionButton>
                  ) : null}
                </View>
              );
            })}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", justifyContent: "space-between", gap: 12 },
  title: { flex: 1, color: "#111827", fontSize: 15, fontWeight: "700" },
  state: { color: "#1d4ed8", fontSize: 12, fontWeight: "700" },
  metric: { color: "#111827", fontSize: 22, fontWeight: "800" },
  error: { color: "#b91c1c", lineHeight: 20 },
  sectionTitle: { color: "#111827", fontSize: 20, fontWeight: "800" },
});
