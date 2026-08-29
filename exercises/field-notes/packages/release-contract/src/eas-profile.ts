import type { EasAssessment } from "./types.ts";

function object(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function secretLike(key: string, value: unknown): boolean {
  if (/(secret|token|password|credential|private|api[_-]?key)/i.test(key)) return true;
  return typeof value === "string" && (/^https?:\/\//i.test(value) || /-----BEGIN [A-Z ]+-----/.test(value));
}

export function validateEasConfiguration(input: unknown): EasAssessment {
  const errors: string[] = [];
  const root = object(input);
  if (!root) errors.push("configuration must be an object");
  const cli = object(root?.cli);
  const build = object(root?.build);

  if (cli?.requireCommit !== true) errors.push("cli.requireCommit must be true");
  if (cli?.appVersionSource !== "local") errors.push("cli.appVersionSource must be local");
  if (!build) errors.push("build profiles are required");

  const expectedProfiles = ["base", "development", "preview", "production"];
  if (build) {
    const actual = Object.keys(build).sort();
    if (JSON.stringify(actual) !== JSON.stringify([...expectedProfiles].sort())) {
      errors.push("build must contain exactly base, development, preview, and production profiles");
    }
  }

  const base = object(build?.base);
  const development = object(build?.development);
  const preview = object(build?.preview);
  const production = object(build?.production);
  if (base?.node !== "24.19.0") errors.push("base.node must be 24.19.0");

  for (const [name, profile] of [
    ["development", development],
    ["preview", preview],
    ["production", production],
  ] as const) {
    if (!profile) {
      errors.push(`${name} profile is required`);
      continue;
    }
    if (profile.extends !== "base") errors.push(`${name}.extends must be base`);
    if ("channel" in profile) errors.push(`${name}.channel is outside this build-only contract`);
    if ("node" in profile && profile.node !== "24.19.0") {
      errors.push(`${name}.node must not override the runtime pin`);
    }
    const android = object(profile.android);
    const ios = object(profile.ios);
    if (android && "node" in android) errors.push(`${name}.android.node override is forbidden`);
    if (ios && "node" in ios) errors.push(`${name}.ios.node override is forbidden`);

    const env = object(profile.env);
    if (!env || Object.keys(env).length !== 1 || env.FIELD_NOTES_BUILD_PROFILE !== name) {
      errors.push(`${name}.env must contain only FIELD_NOTES_BUILD_PROFILE=${name}`);
    } else {
      for (const [key, value] of Object.entries(env)) {
        if (secretLike(key, value)) errors.push(`${name}.env contains secret-like material`);
      }
    }
  }

  if (development) {
    if (development.developmentClient !== true) errors.push("development.developmentClient must be true");
    if (development.distribution !== "internal") errors.push("development.distribution must be internal");
  }
  if (preview) {
    if (preview.developmentClient === true) errors.push("preview must not be a development client");
    if (preview.distribution !== "internal") errors.push("preview.distribution must be internal");
    if (object(preview.android)?.buildType !== "apk") errors.push("preview.android.buildType must be apk");
  }
  if (production) {
    if (production.developmentClient === true) errors.push("production must not be a development client");
    if (production.distribution === "internal") errors.push("production must not use internal distribution");
    if (object(production.android)?.buildType === "apk") errors.push("production must retain the default AAB output");
  }

  return {
    configurationValid: errors.length === 0,
    errors,
    guarantees: {
      nativeBuildExecuted: false,
      artifactBytesVerified: false,
      signingVerified: false,
      installationVerified: false,
      storeAccepted: false,
      updatePublished: false,
    },
  };
}
