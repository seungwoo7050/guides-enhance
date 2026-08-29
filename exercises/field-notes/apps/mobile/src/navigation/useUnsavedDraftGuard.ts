import {
  OneShotNavigationPermit,
  handlePreventedDraftNavigation,
} from "@field-notes/core";
import { useNavigation } from "expo-router";
import { usePreventRemove } from "expo-router/build/react-navigation/core";
import { useCallback, useRef } from "react";
import { Alert } from "react-native";

export function useUnsavedDraftGuard(
  dirty: boolean,
): {
  requestLeave(): void;
  leaveAfterCommit(navigate: () => void): void;
} {
  const navigation = useNavigation();
  const permit = useRef(new OneShotNavigationPermit()).current;

  const confirmDiscard = useCallback((discard: () => void) => {
    Alert.alert(
      "Discard unsaved changes?",
      "Leaving this screen will remove the current draft changes.",
      [
        { text: "Keep editing", style: "cancel" },
        { text: "Discard", style: "destructive", onPress: discard },
      ],
    );
  }, []);

  usePreventRemove(dirty, ({ data }) => {
    handlePreventedDraftNavigation(
      permit,
      confirmDiscard,
      () => navigation.dispatch(data.action),
    );
  });

  const requestLeave = useCallback(() => navigation.goBack(), [navigation]);
  const leaveAfterCommit = useCallback((navigate: () => void) => {
    permit.grant();
    try {
      navigate();
    } finally {
      permit.revoke();
    }
  }, [permit]);

  return { requestLeave, leaveAfterCommit };
}
