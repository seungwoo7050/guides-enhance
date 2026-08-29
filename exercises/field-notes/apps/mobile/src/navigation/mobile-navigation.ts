import {
  CrossSourceRouteArbiter,
  LatestNavigationIntentBuffer,
  RecentIntentSet,
  applyReservedRoute,
  decideNavigation,
  navigationIntentKey,
  parseNavigationIntent,
  type NavigationIntent,
  type NavigationIntentPort,
} from "@field-notes/core";
import Constants from "expo-constants";
import * as Linking from "expo-linking";

type LinkSource = {
  getInitialURL(): Promise<string | null>;
  addEventListener(
    eventName: "url",
    listener: (event: { url: string }) => void,
  ): { remove(): void };
};

export function resolvedAppScheme(
  configured: string | string[] | undefined = Constants.expoConfig?.scheme,
): string {
  if (typeof configured !== "string" || configured.length === 0) {
    throw new Error("resolved Expo app config must contain exactly one non-empty scheme");
  }
  return configured;
}

export class ExpoLinkIntentAdapter implements NavigationIntentPort {
  readonly #expectedScheme: string;
  readonly #source: LinkSource;

  public constructor(
    expectedScheme = resolvedAppScheme(),
    source: LinkSource = Linking,
  ) {
    this.#expectedScheme = expectedScheme;
    this.#source = source;
  }

  public async initial(): Promise<NavigationIntent | null> {
    const url = await this.#source.getInitialURL();
    return url === null
      ? null
      : parseNavigationIntent(url, "link", this.#expectedScheme);
  }

  public subscribe(listener: (intent: NavigationIntent) => void): () => void {
    const subscription = this.#source.addEventListener("url", ({ url }) => {
      listener(parseNavigationIntent(url, "link", this.#expectedScheme));
    });
    return () => subscription.remove();
  }
}

function noticeHref(intent: NavigationIntent, reason: string): string {
  const notice = intent.kind === "open-record"
    ? `missing:${intent.recordId}`
    : `invalid:${reason}`;
  return `/records?navigationNotice=${encodeURIComponent(notice)}`;
}

export type LinkNavigationController = {
  dispose(): void;
  retryDeferred(): void;
};

export function installLinkNavigation(input: {
  adapter?: NavigationIntentPort;
  initialPathname: string;
  arbiter: CrossSourceRouteArbiter;
  isDraftActive?(): boolean;
  recordExists(recordId: string): Promise<boolean>;
  navigate(href: string): void;
  reportFailure(error: unknown): void;
}): LinkNavigationController {
  const adapter = input.adapter ?? new ExpoLinkIntentAdapter();
  const recent = new RecentIntentSet();
  const pendingWarm = new LatestNavigationIntentBuffer();
  const deferredByDraft = new LatestNavigationIntentBuffer();
  let active = true;
  let bootstrapped = false;
  let deliveryTail: Promise<void> = Promise.resolve();

  const deliver = async (intent: NavigationIntent): Promise<void> => {
    if (input.isDraftActive?.()) {
      deferredByDraft.offer(intent);
      return;
    }
    const intentKey = navigationIntentKey(intent);
    if (!recent.accept(intentKey)) return;
    try {
      const decision = await decideNavigation({
        intent,
        alreadyProcessed: false,
        recordExists: input.recordExists,
      });
      if (!active || decision.kind === "duplicate") return;
      const href = decision.kind === "navigate"
        ? decision.href
        : noticeHref(
            intent,
            decision.kind === "missing-record" ? decision.recordId : decision.reason,
          );
      const reservation = input.arbiter.reserve(href);
      if (reservation === null) return;
      applyReservedRoute(reservation, () => input.navigate(href));
    } catch (error) {
      recent.forget(intentKey);
      throw error;
    }
  };

  const schedule = (intent: NavigationIntent): void => {
    deliveryTail = deliveryTail
      .then(() => deliver(intent))
      .catch((error) => {
        if (active) input.reportFailure(error);
      });
  };

  const unsubscribe = adapter.subscribe((intent) => {
    if (!bootstrapped) {
      pendingWarm.offer(intent);
      return;
    }
    schedule(intent);
  });

  void (async () => {
    try {
      const initial = await adapter.initial();
      if (!active) return;
      if (initial !== null) {
        await deliver(initial);
      } else if (input.initialPathname !== "/") {
        await deliver(parseNavigationIntent(input.initialPathname, "restoration"));
      }
      let queued = pendingWarm.take();
      while (queued !== null) {
        await deliver(queued);
        queued = pendingWarm.take();
      }
      bootstrapped = true;
    } catch (error) {
      if (active) input.reportFailure(error);
    }
  })();

  return {
    dispose() {
      active = false;
      unsubscribe();
    },
    retryDeferred() {
      if (!active || input.isDraftActive?.()) return;
      const intent = deferredByDraft.take();
      if (intent !== null) schedule(intent);
    },
  };
}
