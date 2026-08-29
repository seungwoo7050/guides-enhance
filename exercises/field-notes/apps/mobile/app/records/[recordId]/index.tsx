import { Link, useLocalSearchParams, useRouter } from "expo-router";
import { Alert, Pressable, StyleSheet, Text, View } from "react-native";
import { useFieldNotes } from "../../../src/application/FieldNotesRuntime";
import { ActionButton } from "../../../src/components/ActionButton";
import { Screen, commonStyles } from "../../../src/components/Screen";
import { StateNotice } from "../../../src/components/StateNotice";

function firstParameter(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] ?? "" : value ?? "";
}

export default function RecordDetailRoute() {
  const router = useRouter();
  const params = useLocalSearchParams<{ recordId?: string | string[] }>();
  const recordId = firstParameter(params.recordId);
  const runtime = useFieldNotes();
  const record = runtime.record(recordId);
  const attachments = runtime.attachmentsFor(recordId);

  if (!runtime.ready) {
    return <Screen title="Record"><StateNotice message="Loading local state…" /></Screen>;
  }
  if (!record) {
    return (
      <Screen title="Record unavailable" subtitle="The record does not exist or has been deleted locally.">
        <Link href="/records" style={styles.link}>Return to records</Link>
      </Screen>
    );
  }

  const remove = () => {
    Alert.alert(
      "Delete this record?",
      "The deletion is committed locally and queued for synchronization.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete",
          style: "destructive",
          onPress: () => void runtime.deleteRecord(record.id, record.localRevision)
            .then(() => router.replace("/records"))
            .catch(() => undefined),
        },
      ],
    );
  };

  return (
    <Screen
      title={record.title}
      subtitle={`Local revision ${record.localRevision} · Remote version ${record.remoteVersion ?? "none"}`}
      actions={(
        <>
          <Link href={`/records/${record.id}/edit` as never} asChild>
            <Pressable style={styles.editLink}>
              <Text style={styles.editLabel}>Edit record</Text>
            </Pressable>
          </Link>
          <ActionButton busy={runtime.busy} variant="danger" onPress={remove}>Delete record</ActionButton>
        </>
      )}
    >
      {runtime.error ? <StateNotice kind="error" message={runtime.error} /> : null}
      <View style={commonStyles.card}>
        <Text style={commonStyles.label}>Status</Text>
        <Text style={styles.value}>{record.status}</Text>
        <Text style={commonStyles.label}>Sync state</Text>
        <Text style={styles.value}>{record.syncState}</Text>
        <Text style={commonStyles.label}>Observed</Text>
        <Text style={styles.value}>{new Date(record.observedAt).toLocaleString()}</Text>
      </View>
      <View style={commonStyles.card}>
        <Text style={commonStyles.label}>Notes</Text>
        <Text style={styles.notes}>{record.notes || "No notes"}</Text>
      </View>
      {record.location ? (
        <View style={commonStyles.card}>
          <Text style={commonStyles.label}>Location</Text>
          <Text style={styles.value}>
            {record.location.latitude.toFixed(5)}, {record.location.longitude.toFixed(5)} · ±{Math.round(record.location.accuracyMeters)} m
          </Text>
          <Text style={commonStyles.muted}>Measured {new Date(record.location.measuredAt).toLocaleString()}</Text>
        </View>
      ) : null}
      <View style={commonStyles.card}>
        <Text style={commonStyles.label}>Attachments</Text>
        {attachments.length === 0
          ? <Text style={commonStyles.muted}>No app-owned attachments</Text>
          : attachments.map((attachment) => (
              <View key={attachment.id} style={styles.attachment}>
                <Text numberOfLines={1} style={styles.attachmentName}>{attachment.id}</Text>
                <Text style={commonStyles.muted}>
                  {attachment.state} · {Math.round(attachment.byteSize / 1024)} KB
                </Text>
              </View>
            ))}
        <ActionButton
          busy={runtime.busy}
          variant="secondary"
          onPress={() => void runtime.attachMedia(record.id, "photo-picker")}
        >
          Choose photo
        </ActionButton>
        <ActionButton
          busy={runtime.busy}
          variant="secondary"
          onPress={() => void runtime.attachMedia(record.id, "camera")}
        >
          Take photo
        </ActionButton>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  value: { color: "#111827", fontSize: 16 },
  notes: { color: "#1f2937", fontSize: 16, lineHeight: 24 },
  link: { color: "#1d4ed8", fontSize: 16, fontWeight: "700" },
  editLink: {
    alignItems: "center",
    justifyContent: "center",
    minHeight: 48,
    borderRadius: 12,
    backgroundColor: "#e5e7eb",
    paddingHorizontal: 18,
  },
  editLabel: { color: "#1f2937", fontSize: 16, fontWeight: "700" },
  attachment: { gap: 2, paddingVertical: 4 },
  attachmentName: { color: "#111827", fontWeight: "600" },
});
