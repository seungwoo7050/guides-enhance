const staticExpoConfig = require("./app.json").expo;

const PROFILE_ENV = "FIELD_NOTES_BUILD_PROFILE";
const SYNC_URL_ENV = "EXPO_PUBLIC_FIELD_NOTES_SYNC_URL";

const PROFILES = Object.freeze({
  development: Object.freeze({
    name: "Field Notes Development",
    applicationId: "dev.seungwoo7050.fieldnotes.development",
    scheme: "fieldnotes-development",
    addGeneratedDevClientScheme: true,
  }),
  preview: Object.freeze({
    name: "Field Notes Preview",
    applicationId: "dev.seungwoo7050.fieldnotes.preview",
    scheme: "fieldnotes-preview",
    addGeneratedDevClientScheme: false,
  }),
  production: Object.freeze({
    name: "Field Notes",
    applicationId: "dev.seungwoo7050.fieldnotes",
    scheme: "fieldnotes",
    addGeneratedDevClientScheme: false,
  }),
});

function selectedProfile(environment = process.env) {
  const value = environment[PROFILE_ENV];
  const profileName = value === undefined ? "development" : value;
  const profile = PROFILES[profileName];
  if (profile === undefined) {
    throw new Error(
      `${PROFILE_ENV} must be exactly development, preview, or production; received ${JSON.stringify(profileName)}`,
    );
  }
  return { profileName, profile };
}

function resolvedSyncUrl(environment, profileName) {
  const candidate = environment[SYNC_URL_ENV]
    ?? (profileName === "development" ? "http://127.0.0.1:8787" : undefined);
  if (typeof candidate !== "string" || candidate.length === 0) {
    throw new Error(`${SYNC_URL_ENV} is required for ${profileName} builds`);
  }
  let url;
  try {
    url = new URL(candidate);
  } catch {
    throw new Error(`${SYNC_URL_ENV} must be an absolute URL`);
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new Error(`${SYNC_URL_ENV} must use http or https`);
  }
  return url.toString().replace(/\/$/, "");
}

function profileDevClientPlugin(plugins, addGeneratedScheme) {
  if (!Array.isArray(plugins)) {
    throw new Error("static app config must declare the expo-dev-client plugin");
  }
  let matches = 0;
  const resolved = plugins.map((entry) => {
    const pluginName = Array.isArray(entry) ? entry[0] : entry;
    if (pluginName !== "expo-dev-client") return entry;
    matches += 1;
    const existingOptions = Array.isArray(entry) ? entry[1] : undefined;
    if (
      existingOptions !== undefined
      && (typeof existingOptions !== "object" || existingOptions === null || Array.isArray(existingOptions))
    ) {
      throw new Error("expo-dev-client plugin options must be an object");
    }
    return [
      "expo-dev-client",
      { ...(existingOptions ?? {}), addGeneratedScheme },
    ];
  });
  if (matches !== 1) {
    throw new Error("static app config must declare expo-dev-client exactly once");
  }
  return resolved;
}

/**
 * 설치 프로필마다 application ID와 scheme을 분리합니다.
 * 동기화 URL은 공개 런타임 설정이며 인증 정보는 Expo config나
 * JavaScript 번들에 넣지 않습니다.
 */
function resolveConfig(environment = process.env, baseConfig = staticExpoConfig) {
  const { profileName, profile } = selectedProfile(environment);
  return {
    ...baseConfig,
    name: profile.name,
    scheme: profile.scheme,
    plugins: profileDevClientPlugin(
      baseConfig.plugins,
      profile.addGeneratedDevClientScheme,
    ),
    ios: {
      ...baseConfig.ios,
      bundleIdentifier: profile.applicationId,
    },
    android: {
      ...baseConfig.android,
      package: profile.applicationId,
    },
    extra: {
      ...baseConfig.extra,
      fieldNotes: {
        ...(baseConfig.extra?.fieldNotes ?? {}),
        buildProfile: profileName,
        appIdentityLabel: profileName,
        syncUrl: resolvedSyncUrl(environment, profileName),
      },
    },
  };
}

module.exports = ({ config = staticExpoConfig } = {}) =>
  resolveConfig(process.env, config);

Object.defineProperties(module.exports, {
  resolveConfig: { value: resolveConfig },
  selectedProfile: { value: selectedProfile },
  resolvedSyncUrl: { value: resolvedSyncUrl },
});
