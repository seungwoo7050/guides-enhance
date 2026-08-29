import { Link, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { StyleSheet } from "react-native";
import { useFieldNotes } from "../../../src/application/FieldNotesRuntime";
import { RecordForm } from "../../../src/components/RecordForm";
import { useUnsavedDraftGuard } from "../../../src/navigation/useUnsavedDraftGuard";
import { Screen } from "../../../src/components/Screen";
import { StateNotice } from "../../../src/components/StateNotice";

function firstParameter(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] ?? "" : value ?? "";
}

export default function EditRecordRoute() {
  const router = useRouter();
  const params = useLocalSearchParams<{ recordId?: string | string[] }>();
  const recordId = firstParameter(params.recordId);
  const runtime = useFieldNotes();
  const record = runtime.record(recordId);
  const [dirty, setDirty] = useState(false);
  const { leaveAfterCommit, requestLeave } = useUnsavedDraftGuard(dirty);
  const handleDirtyChange = useCallback((value: boolean) => setDirty(value), []);

  useEffect(() => {
    runtime.setDraftActive(true);
    return () => runtime.setDraftActive(false);
  }, [runtime.setDraftActive]);

  if (!runtime.ready) {
    return <Screen title="Edit record"><StateNotice message="Loading local state…" /></Screen>;
  }
  if (!record) {
    return (
      <Screen title="Record unavailable">
        <StateNotice kind="warning" message="This record does not exist or was deleted." />
        <Link href="/records" style={styles.link}>Return to records</Link>
      </Screen>
    );
  }

  return (
    <Screen
      title="Edit record"
      subtitle={`Changes are based on local revision ${record.localRevision}. A concurrent update is rejected instead of overwritten.`}
    >
      <RecordForm
        initial={record}
        busy={runtime.busy}
        onCancel={requestLeave}
        onDirtyChange={handleDirtyChange}
        onMeasureLocation={runtime.measureLocation}
        onSubmit={async (payload) => {
          await runtime.updateRecord(record.id, record.localRevision, payload);
          leaveAfterCommit(() => router.replace(`/records/${record.id}` as never));
        }}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  link: { color: "#1d4ed8", fontSize: 16, fontWeight: "700" },
});
