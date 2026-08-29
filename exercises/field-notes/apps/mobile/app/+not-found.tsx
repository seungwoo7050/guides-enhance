import { Link } from "expo-router";
import { StyleSheet, Text } from "react-native";
import { Screen } from "../src/components/Screen";

export default function NotFoundRoute() {
  return (
    <Screen title="Route not found" subtitle="The requested Field Notes destination is unavailable.">
      <Link href="/records" style={styles.link}>Return to records</Link>
    </Screen>
  );
}

const styles = StyleSheet.create({
  link: { color: "#1d4ed8", fontSize: 16, fontWeight: "700" },
});
