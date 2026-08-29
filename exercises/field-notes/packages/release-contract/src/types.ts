export type Platform = "android" | "ios";

export type ArtifactKind =
  | "android-aab"
  | "android-apk"
  | "android-play-split-set"
  | "ios-xcarchive"
  | "ios-ipa"
  | "ios-testflight-build"
  | "ios-simulator-app";

export type ArtifactIdentity =
  | {
      kind: "local-bytes";
      fileName: string;
      byteSize: number;
      sha256: string;
    }
  | {
      kind: "directory-tree";
      directoryName: string;
      fileCount: number;
      byteSize: number;
      treeDigestAlgorithm: "sha256-canonical-tree-v1";
      treeSha256: string;
    }
  | {
      kind: "store-build";
      provider: "google-play" | "app-store-connect";
      buildId: string;
    };

export type SigningEvidence =
  | { status: "not-run"; reason: string }
  | {
      status: "claimed";
      identity: string;
      observedAt: string;
      evidenceRef: string;
    }
  | {
      status: "manually-reviewed";
      identity: string;
      observedAt: string;
      evidenceRef: string;
      reviewer: string;
      reviewedAt: string;
      reviewEvidenceRef: string;
    };

export type ReleaseArtifact = {
  ref: string;
  kind: ArtifactKind;
  identity: ArtifactIdentity;
  signing: SigningEvidence;
};

export type InstallationEvidence =
  | { status: "not-run"; reason: string }
  | {
      status: "verified";
      artifactRef: string;
      deviceClass: "physical" | "emulator" | "simulator";
      redactedDeviceId: string;
      observedApplicationId: string;
      observedVersion: string;
      observedBuildNumber: string;
      observedRuntimeVersion: string;
      observedRuntimeFingerprint: string;
      launchResult: "passed" | "failed";
      observedAt: string;
      evidenceRef: string;
    };

export type StoreEvidence =
  | { status: "not-run"; reason: string }
  | {
      status: "submitted" | "accepted";
      artifactRef: string;
      provider: "google-play" | "app-store-connect";
      observedAt: string;
      evidenceRef: string;
    };

export type ReleaseEvidence = {
  schemaVersion: 2;
  source: {
    revision: string;
    treeSha256: string;
    lockSha256: string;
  };
  application: {
    platform: Platform;
    applicationId: string;
    version: string;
    buildNumber: string;
    runtimeVersion: string;
    runtimeFingerprint: string;
  };
  build: {
    profile: "development" | "preview" | "production";
    tool: string;
    generatedConfigSha256: string;
  };
  artifacts: ReleaseArtifact[];
  installation: InstallationEvidence;
  store: StoreEvidence;
};

export type ManifestAssessment = {
  platform: Platform | null;
  consistent: boolean;
  artifactSetComplete: boolean;
  physicalDeviceEvidenceConsistent: boolean;
  errors: string[];
  warnings: string[];
};

export type ReleasePairAssessment = {
  consistent: boolean;
  sameCandidate: boolean;
  crossPlatformPhysicalEvidenceConsistent: boolean;
  android: ManifestAssessment;
  ios: ManifestAssessment;
  errors: string[];
  guarantees: {
    nativeBuildExecuted: false;
    artifactBytesVerified: false;
    signingTrustVerified: false;
    installationExecuted: false;
    storeAccepted: false;
    remoteUpdateDelivered: false;
  };
};

export type EasAssessment = {
  configurationValid: boolean;
  errors: string[];
  guarantees: {
    nativeBuildExecuted: false;
    artifactBytesVerified: false;
    signingVerified: false;
    installationVerified: false;
    storeAccepted: false;
    updatePublished: false;
  };
};
