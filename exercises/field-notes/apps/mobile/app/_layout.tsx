import { FieldNotesProvider } from "../src/application/FieldNotesRuntime";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <FieldNotesProvider>
        <StatusBar style="auto" />
        <Stack
          screenOptions={{
            headerBackTitle: "Back",
            headerShadowVisible: false,
            headerStyle: { backgroundColor: "#f8fafc" },
            headerTitleStyle: { color: "#111827", fontWeight: "700" },
          }}
        >
          <Stack.Screen name="index" options={{ headerShown: false }} />
          <Stack.Screen name="records/index" options={{ title: "Field Notes" }} />
          <Stack.Screen name="records/new" options={{ title: "New record" }} />
          <Stack.Screen name="records/[recordId]/index" options={{ title: "Record" }} />
          <Stack.Screen name="records/[recordId]/edit" options={{ title: "Edit record" }} />
          <Stack.Screen name="sync" options={{ title: "Sync status" }} />
          <Stack.Screen name="settings" options={{ title: "Settings" }} />
        </Stack>
      </FieldNotesProvider>
    </SafeAreaProvider>
  );
}
