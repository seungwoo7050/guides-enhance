import type { RecordLocation, RecordPayload, RecordStatus } from "@field-notes/core";
import { useEffect, useMemo, useRef, useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { ActionButton } from "./ActionButton";
import { commonStyles } from "./Screen";

const statuses: RecordStatus[] = ["draft", "open", "resolved"];

export function RecordForm({
  initial,
  busy,
  onCancel,
  onDirtyChange,
  onMeasureLocation,
  onSubmit,
}: {
  initial?: RecordPayload;
  busy: boolean;
  onCancel?(): void;
  onDirtyChange?(dirty: boolean): void;
  onMeasureLocation(): Promise<RecordLocation>;
  onSubmit(payload: RecordPayload): Promise<void>;
}) {
  const [title, setTitle] = useState(initial?.title ?? "");
  const [notes, setNotes] = useState(initial?.notes ?? "");
  const [status, setStatus] = useState<RecordStatus>(initial?.status ?? "draft");
  const [location, setLocation] = useState<RecordLocation | undefined>(initial?.location);
  const [error, setError] = useState<string | null>(null);
  const baseline = useRef({
    title: initial?.title ?? "",
    notes: initial?.notes ?? "",
    status: initial?.status ?? "draft",
    location: initial?.location,
  }).current;
  const valid = useMemo(() => title.trim().length > 0 && title.trim().length <= 120, [title]);
  const dirty = title !== baseline.title
    || notes !== baseline.notes
    || status !== baseline.status
    || JSON.stringify(location) !== JSON.stringify(baseline.location);

  useEffect(() => {
    onDirtyChange?.(dirty);
  }, [dirty, onDirtyChange]);

  const submit = async () => {
    setError(null);
    if (!valid) {
      setError("Title is required and must be at most 120 characters.");
      return;
    }
    try {
      await onSubmit({
        title: title.trim(),
        notes: notes.trim(),
        status,
        observedAt: initial?.observedAt ?? new Date().toISOString(),
        ...(location ? { location } : {}),
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    }
  };

  return (
    <View style={styles.form}>
      <View style={styles.field}>
        <Text style={commonStyles.label}>Title</Text>
        <TextInput
          accessibilityLabel="Record title"
          editable={!busy}
          maxLength={120}
          onChangeText={setTitle}
          placeholder="What did you observe?"
          style={styles.input}
          value={title}
        />
      </View>
      <View style={styles.field}>
        <Text style={commonStyles.label}>Notes</Text>
        <TextInput
          accessibilityLabel="Record notes"
          editable={!busy}
          multiline
          onChangeText={setNotes}
          placeholder="Add measurements, context, and follow-up details"
          style={[styles.input, styles.multiline]}
          textAlignVertical="top"
          value={notes}
        />
      </View>
      <View style={styles.field}>
        <Text style={commonStyles.label}>Status</Text>
        <View style={styles.statuses}>
          {statuses.map((value) => (
            <Pressable
              accessibilityRole="radio"
              accessibilityState={{ checked: status === value }}
              disabled={busy}
              key={value}
              onPress={() => setStatus(value)}
              style={[styles.status, status === value && styles.selected]}
            >
              <Text style={status === value ? styles.selectedText : styles.statusText}>{value}</Text>
            </Pressable>
          ))}
        </View>
      </View>
      <View style={commonStyles.card}>
        <Text style={commonStyles.label}>Location</Text>
        <Text style={commonStyles.muted}>
          {location
            ? `${location.latitude.toFixed(5)}, ${location.longitude.toFixed(5)} · ±${Math.round(location.accuracyMeters)} m`
            : "No location attached"}
        </Text>
        <ActionButton
          disabled={busy}
          variant="secondary"
          onPress={() => void onMeasureLocation().then(setLocation).catch((caught) => setError(String(caught)))}
        >
          Measure current location
        </ActionButton>
      </View>
      {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
      <ActionButton busy={busy} disabled={!valid} onPress={() => void submit()}>
        Save record
      </ActionButton>
      {onCancel ? (
        <ActionButton disabled={busy} variant="secondary" onPress={onCancel}>
          Cancel
        </ActionButton>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  form: { gap: 16 },
  field: { gap: 7 },
  input: {
    backgroundColor: "white",
    borderColor: "#cbd5e1",
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: 12,
    minHeight: 48,
    paddingHorizontal: 14,
    color: "#111827",
    fontSize: 16,
  },
  multiline: { minHeight: 150, paddingTop: 12 },
  statuses: { flexDirection: "row", gap: 8 },
  status: { paddingVertical: 10, paddingHorizontal: 14, borderRadius: 999, backgroundColor: "#e5e7eb" },
  selected: { backgroundColor: "#1d4ed8" },
  statusText: { color: "#374151", fontWeight: "600" },
  selectedText: { color: "white", fontWeight: "700" },
  error: { color: "#b91c1c", lineHeight: 20 },
});
