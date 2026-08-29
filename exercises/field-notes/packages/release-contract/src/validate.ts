import type {
  ArtifactKind,
  InstallationEvidence,
  ManifestAssessment,
  Platform,
  ReleaseArtifact,
  ReleaseEvidence,
  ReleasePairAssessment,
} from "./types.ts";

const SHA256 = /^[a-f0-9]{64}$/;
const REF = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;

function object(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function isPlatform(value: unknown): value is Platform {
  return value === "android" || value === "ios";
}

function platformForKind(kind: ArtifactKind): Platform {
  return kind.startsWith("android-") ? "android" : "ios";
}

function installableOn(kind: ArtifactKind, deviceClass: string): boolean {
  if (kind === "android-apk") return deviceClass === "physical" || deviceClass === "emulator";
  if (kind === "android-play-split-set") return deviceClass === "physical";
  if (kind === "ios-ipa" || kind === "ios-testflight-build") return deviceClass === "physical";
  if (kind === "ios-simulator-app") return deviceClass === "simulator";
  return false;
}

function parseEvidence(value: unknown, errors: string[]): ReleaseEvidence | null {
  const root = object(value);
  if (!root) {
    errors.push("manifest must be an object");
    return null;
  }
  if (root.schemaVersion !== 2) errors.push("schemaVersion must be 2");
  const source = object(root.source);
  const application = object(root.application);
  const build = object(root.build);
  if (!source) errors.push("source is required");
  if (!application) errors.push("application is required");
  if (!build) errors.push("build is required");
  if (!Array.isArray(root.artifacts)) errors.push("artifacts must be an array");
  if (!object(root.installation)) errors.push("installation is required");
  if (!object(root.store)) errors.push("store is required");
  if (errors.length > 0) return null;
  return value as ReleaseEvidence;
}

function validateArtifact(
  artifact: ReleaseArtifact,
  platform: Platform,
  errors: string[],
): void {
  if (!REF.test(artifact.ref)) errors.push(`invalid artifact ref: ${artifact.ref}`);
  if (platformForKind(artifact.kind) !== platform) {
    errors.push(`${artifact.ref} belongs to another platform`);
  }

  const identity = artifact.identity;
  if (identity.kind === "local-bytes") {
    if (identity.byteSize < 1 || !Number.isInteger(identity.byteSize)) {
      errors.push(`${artifact.ref} has an invalid byteSize`);
    }
    if (!SHA256.test(identity.sha256)) errors.push(`${artifact.ref} has an invalid sha256`);
    if (["ios-xcarchive", "ios-simulator-app", "android-play-split-set", "ios-testflight-build"].includes(artifact.kind)) {
      errors.push(`${artifact.ref} uses the wrong identity kind`);
    }
  } else if (identity.kind === "directory-tree") {
    if (identity.treeDigestAlgorithm !== "sha256-canonical-tree-v1") {
      errors.push(`${artifact.ref} has an unsupported tree digest algorithm`);
    }
    if (!SHA256.test(identity.treeSha256)) errors.push(`${artifact.ref} has an invalid treeSha256`);
    if (!Number.isInteger(identity.fileCount) || identity.fileCount < 1) {
      errors.push(`${artifact.ref} has an invalid fileCount`);
    }
    if (!Number.isInteger(identity.byteSize) || identity.byteSize < 1) {
      errors.push(`${artifact.ref} has an invalid byteSize`);
    }
    if (artifact.kind !== "ios-xcarchive" && artifact.kind !== "ios-simulator-app") {
      errors.push(`${artifact.ref} uses the wrong identity kind`);
    }
  } else if (identity.kind === "store-build") {
    if (!REF.test(identity.buildId)) errors.push(`${artifact.ref} has an invalid store build id`);
    if (artifact.kind !== "android-play-split-set" && artifact.kind !== "ios-testflight-build") {
      errors.push(`${artifact.ref} uses the wrong identity kind`);
    }
  } else {
    errors.push(`${artifact.ref} has an unknown identity kind`);
  }

  if (!artifact.signing || !["not-run", "claimed", "manually-reviewed"].includes(artifact.signing.status)) {
    errors.push(`${artifact.ref} has invalid signing evidence`);
  }
}

function validateInstallation(
  manifest: ReleaseEvidence,
  artifacts: Map<string, ReleaseArtifact>,
  errors: string[],
): boolean {
  const installation = manifest.installation;
  if (installation.status === "not-run") return false;
  const artifact = artifacts.get(installation.artifactRef);
  if (!artifact) {
    errors.push("installation references an unknown artifact");
    return false;
  }
  if (!installableOn(artifact.kind, installation.deviceClass)) {
    errors.push(`${artifact.kind} is not installable on ${installation.deviceClass}`);
  }
  if (installation.launchResult !== "passed") errors.push("verified installation requires a passed launch");
  if (installation.observedApplicationId !== manifest.application.applicationId) {
    errors.push("installed applicationId does not match the build candidate");
  }
  if (installation.observedVersion !== manifest.application.version) {
    errors.push("installed version does not match the build candidate");
  }
  if (installation.observedBuildNumber !== manifest.application.buildNumber) {
    errors.push("installed build number does not match the build candidate");
  }
  if (installation.observedRuntimeVersion !== manifest.application.runtimeVersion) {
    errors.push("installed runtimeVersion does not match the build candidate");
  }
  if (installation.observedRuntimeFingerprint !== manifest.application.runtimeFingerprint) {
    errors.push("installed runtime fingerprint does not match the build candidate");
  }
  return installation.deviceClass === "physical" && errors.length === 0;
}

function artifactSetComplete(platform: Platform, artifacts: ReleaseArtifact[]): boolean {
  const kinds = new Set(artifacts.map((artifact) => artifact.kind));
  return platform === "android"
    ? kinds.has("android-aab") && (kinds.has("android-apk") || kinds.has("android-play-split-set"))
    : kinds.has("ios-xcarchive") && (kinds.has("ios-ipa") || kinds.has("ios-testflight-build"));
}

export function validateReleaseManifest(value: unknown): {
  evidence: ReleaseEvidence | null;
  assessment: ManifestAssessment;
} {
  const errors: string[] = [];
  const warnings: string[] = [];
  const evidence = parseEvidence(value, errors);
  const platform = evidence && isPlatform(evidence.application.platform)
    ? evidence.application.platform
    : null;
  if (evidence && !platform) errors.push("application.platform must be android or ios");

  if (evidence && platform) {
    if (!SHA256.test(evidence.source.treeSha256)) errors.push("source.treeSha256 is invalid");
    if (!SHA256.test(evidence.source.lockSha256)) errors.push("source.lockSha256 is invalid");
    if (!REF.test(evidence.source.revision)) errors.push("source.revision is invalid");
    if (!SHA256.test(evidence.build.generatedConfigSha256)) {
      errors.push("build.generatedConfigSha256 is invalid");
    }
    if (!REF.test(evidence.application.runtimeFingerprint)) {
      errors.push("application.runtimeFingerprint is invalid");
    }

    const refs = new Set<string>();
    for (const artifact of evidence.artifacts) {
      if (refs.has(artifact.ref)) errors.push(`duplicate artifact ref: ${artifact.ref}`);
      refs.add(artifact.ref);
      validateArtifact(artifact, platform, errors);
    }
    const artifacts = new Map(evidence.artifacts.map((artifact) => [artifact.ref, artifact]));
    const physical = validateInstallation(evidence, artifacts, errors);

    if (evidence.store.status !== "not-run") {
      const artifact = artifacts.get(evidence.store.artifactRef);
      if (!artifact) errors.push("store evidence references an unknown artifact");
      if (platform === "android" && artifact?.kind !== "android-aab") {
        errors.push("Google Play submission must reference android-aab");
      }
      if (platform === "ios" && artifact?.kind !== "ios-xcarchive" && artifact?.kind !== "ios-ipa") {
        errors.push("App Store submission must reference ios-xcarchive or ios-ipa");
      }
    }

    const complete = artifactSetComplete(platform, evidence.artifacts);
    if (!complete) warnings.push("artifact set is incomplete");
    if (evidence.installation.status === "not-run") warnings.push("physical-device installation was not run");
    return {
      evidence,
      assessment: {
        platform,
        consistent: errors.length === 0,
        artifactSetComplete: complete,
        physicalDeviceEvidenceConsistent: physical && complete && errors.length === 0,
        errors,
        warnings,
      },
    };
  }

  return {
    evidence,
    assessment: {
      platform,
      consistent: false,
      artifactSetComplete: false,
      physicalDeviceEvidenceConsistent: false,
      errors,
      warnings,
    },
  };
}

function candidateIdentity(evidence: ReleaseEvidence): string[] {
  return [
    evidence.source.revision,
    evidence.source.treeSha256,
    evidence.source.lockSha256,
    evidence.build.profile,
    evidence.application.version,
    evidence.application.runtimeVersion,
    evidence.application.runtimeFingerprint,
  ];
}

// [Implementation 10]
// EAS 빌드 프로필과 Android·iOS 릴리스 후보 근거가 서로 일치하는지 검증합니다.
export function validateReleasePair(
  first: unknown,
  second: unknown,
): ReleasePairAssessment {
  const firstResult = validateReleaseManifest(first);
  const secondResult = validateReleaseManifest(second);
  const byPlatform = new Map<Platform, typeof firstResult>();
  if (firstResult.assessment.platform) byPlatform.set(firstResult.assessment.platform, firstResult);
  if (secondResult.assessment.platform) {
    if (byPlatform.has(secondResult.assessment.platform)) {
      secondResult.assessment.errors.push(`duplicate ${secondResult.assessment.platform} manifest`);
      secondResult.assessment.consistent = false;
    }
    byPlatform.set(secondResult.assessment.platform, secondResult);
  }

  const android = byPlatform.get("android") ?? {
    evidence: null,
    assessment: {
      platform: "android" as const,
      consistent: false,
      artifactSetComplete: false,
      physicalDeviceEvidenceConsistent: false,
      errors: ["android manifest is missing"],
      warnings: [],
    },
  };
  const ios = byPlatform.get("ios") ?? {
    evidence: null,
    assessment: {
      platform: "ios" as const,
      consistent: false,
      artifactSetComplete: false,
      physicalDeviceEvidenceConsistent: false,
      errors: ["ios manifest is missing"],
      warnings: [],
    },
  };

  const errors = [...android.assessment.errors, ...ios.assessment.errors];
  let sameCandidate = false;
  if (android.evidence && ios.evidence) {
    const left = candidateIdentity(android.evidence);
    const right = candidateIdentity(ios.evidence);
    sameCandidate = left.every((value, index) => value === right[index]);
    if (!sameCandidate) errors.push("android and ios manifests do not describe the same release candidate");
  }

  // `consistent`는 제출한 값끼리 모순이 없다는 뜻이며 빌드·서명·설치를 실행했다는 뜻은 아닙니다.
  return {
    consistent: errors.length === 0,
    sameCandidate,
    crossPlatformPhysicalEvidenceConsistent: sameCandidate
      && android.assessment.physicalDeviceEvidenceConsistent
      && ios.assessment.physicalDeviceEvidenceConsistent,
    android: android.assessment,
    ios: ios.assessment,
    errors,
    guarantees: {
      nativeBuildExecuted: false,
      artifactBytesVerified: false,
      signingTrustVerified: false,
      installationExecuted: false,
      storeAccepted: false,
      remoteUpdateDelivered: false,
    },
  };
}
