import { useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { useFieldNotes } from "../src/application/FieldNotesRuntime";
import { resolvedBuildProfile, resolvedSyncEndpoint } from "../src/application/runtime-config";
import { ActionButton } from "../src/components/ActionButton";
import { Screen, commonStyles } from "../src/components/Screen";
import { StateNotice } from "../src/components/StateNotice";

function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export default function SettingsRoute() {
  const runtime = useFieldNotes();
  const [notificationStatus, setNotificationStatus] = useState<string | null>(null);
  const [backgroundStatus, setBackgroundStatus] = useState<string | null>(null);
  const buildProfile = resolvedBuildProfile();
  let endpoint = "not configured";
  try {
    endpoint = resolvedSyncEndpoint();
  } catch {
    // 실행 준비 단계에서 실제 설정 오류를 보고하므로 임의의 대체값을 만들지 않습니다.
  }

  useEffect(() => {
    if (!runtime.ready) return;
    void runtime.inspectBackgroundSync()
      .then(setBackgroundStatus)
      .catch((error) => setBackgroundStatus(`error:${message(error)}`));
  }, [runtime.ready]);

  return (
    <Screen
      title="Settings"
      subtitle="Device permission, push token, installation binding, and background registration remain separately observable states."
    >
      {runtime.error ? <StateNotice kind="error" message={runtime.error} /> : null}
      <View style={commonStyles.card}>
        <Text style={commonStyles.label}>Build profile</Text>
        <Text style={styles.value}>{buildProfile}</Text>
        <Text style={commonStyles.label}>Sync endpoint</Text>
        <Text selectable style={styles.endpoint}>{endpoint}</Text>
      </View>
      <View style={commonStyles.card}>
        <Text style={commonStyles.label}>Notifications</Text>
        <Text style={commonStyles.muted}>
          Android channel creation occurs before permission and token acquisition. Token registration is stored against this installation and account.
        </Text>
        <ActionButton
          busy={runtime.busy}
          onPress={() => {
            void runtime.registerNotifications(true)
              .then(setNotificationStatus)
              .catch((error) => setNotificationStatus(`error:${message(error)}`));
          }}
        >
          Enable notifications
        </ActionButton>
        <ActionButton
          busy={runtime.busy}
          variant="secondary"
          onPress={() => {
            void runtime.registerNotifications(false)
              .then(setNotificationStatus)
              .catch((error) => setNotificationStatus(`error:${message(error)}`));
          }}
        >
          Inspect without prompting
        </ActionButton>
        {notificationStatus ? (
          <StateNotice message={`Notification registration: ${notificationStatus}`} />
        ) : null}
      </View>
      <View style={commonStyles.card}>
        <Text style={commonStyles.label}>Background sync</Text>
        <Text style={commonStyles.muted}>
          Registration only gives the OS an opportunity to run. A task reports success only after every claimed command has a durable checkpoint.
        </Text>
        <ActionButton
          busy={runtime.busy}
          onPress={() => {
            void runtime.setBackgroundSync(true)
              .then(setBackgroundStatus)
              .catch((error) => setBackgroundStatus(`error:${message(error)}`));
          }}
        >
          Register background sync
        </ActionButton>
        <ActionButton
          busy={runtime.busy}
          variant="secondary"
          onPress={() => {
            void runtime.setBackgroundSync(false)
              .then(setBackgroundStatus)
              .catch((error) => setBackgroundStatus(`error:${message(error)}`));
          }}
        >
          Unregister background sync
        </ActionButton>
        {backgroundStatus ? (
          <StateNotice message={`Background task: ${backgroundStatus}`} />
        ) : null}
      </View>
      <View style={commonStyles.card}>
        <Text style={commonStyles.label}>Local storage</Text>
        <Text style={commonStyles.muted}>
          Startup reconciles SQLite attachment metadata with the app-owned file directory. Missing files are marked without deleting record data.
        </Text>
        <ActionButton busy={runtime.busy} variant="secondary" onPress={() => void runtime.refresh()}>
          Refresh database view
        </ActionButton>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  value: { color: "#111827", fontSize: 16 },
  endpoint: { color: "#111827", fontFamily: "monospace", fontSize: 13 },
});
