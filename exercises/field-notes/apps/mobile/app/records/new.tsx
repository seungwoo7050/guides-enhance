import { useRouter } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { useFieldNotes } from "../../src/application/FieldNotesRuntime";
import { RecordForm } from "../../src/components/RecordForm";
import { useUnsavedDraftGuard } from "../../src/navigation/useUnsavedDraftGuard";
import { Screen } from "../../src/components/Screen";

export default function NewRecordRoute() {
  const router = useRouter();
  const runtime = useFieldNotes();
  const [dirty, setDirty] = useState(false);
  const { leaveAfterCommit, requestLeave } = useUnsavedDraftGuard(dirty);
  const handleDirtyChange = useCallback((value: boolean) => setDirty(value), []);

  useEffect(() => {
    runtime.setDraftActive(true);
    return () => runtime.setDraftActive(false);
  }, [runtime.setDraftActive]);

  return (
    <Screen
      title="New record"
      subtitle="Saving commits the record and its synchronization command together before this screen closes."
    >
      <RecordForm
        busy={runtime.busy}
        onCancel={requestLeave}
        onDirtyChange={handleDirtyChange}
        onMeasureLocation={runtime.measureLocation}
        onSubmit={async (payload) => {
          const record = await runtime.createRecord(payload);
          leaveAfterCommit(() => router.replace(`/records/${record.id}` as never));
        }}
      />
    </Screen>
  );
}
