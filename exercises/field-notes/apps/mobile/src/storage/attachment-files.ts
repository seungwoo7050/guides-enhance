import type { AttachmentFileStore } from "@field-notes/core";
import * as FileSystem from "expo-file-system/legacy";
import type { SQLiteFieldNotesRepository } from "./SQLiteFieldNotesRepository";
import { createOpaqueId } from "./SQLiteFieldNotesRepository";

export type ExpoAttachmentFileStoreOptions = {
  documentDirectory?: string | null;
};

export class ExpoAttachmentFileStore implements AttachmentFileStore {
  readonly #stagingDirectory: string;
  readonly #ownedDirectory: string;

  constructor(options: ExpoAttachmentFileStoreOptions = {}) {
    const documentDirectory = options.documentDirectory ?? FileSystem.documentDirectory;
    if (!documentDirectory) throw new Error("app document directory is unavailable");
    const root = `${documentDirectory}field-notes/attachments/`;
    this.#stagingDirectory = `${root}staging/`;
    this.#ownedDirectory = `${root}owned/`;
  }

  async #ensureDirectories(): Promise<void> {
    await FileSystem.makeDirectoryAsync(this.#stagingDirectory, { intermediates: true });
    await FileSystem.makeDirectoryAsync(this.#ownedDirectory, { intermediates: true });
  }

  async takeOwnership(temporaryUri: string): Promise<{
    ownedUri: string;
    checksum: string;
    byteSize: number;
  }> {
    if (temporaryUri.trim() === "") throw new Error("temporary media URI is empty");
    await this.#ensureDirectories();
    const identity = createOpaqueId("file");
    if (!/^[A-Za-z0-9-]+$/.test(identity)) throw new Error("generated file identity is not path-safe");
    const stagingUri = `${this.#stagingDirectory}${identity}.partial`;
    const ownedUri = `${this.#ownedDirectory}${identity}.blob`;
    try {
      await FileSystem.copyAsync({ from: temporaryUri, to: stagingUri });
      const info = await FileSystem.getInfoAsync(stagingUri, { md5: true });
      if (
        !info.exists
        || info.isDirectory
        || info.size <= 0
        || !info.md5
      ) {
        throw new Error("copied file is missing, empty, or has no checksum");
      }
      // 검증을 마친 `.partial` 파일만 보관 경로로 옮겨 완료 파일과 작업 중 파일을 구분합니다.
      await FileSystem.moveAsync({ from: stagingUri, to: ownedUri });
      return { ownedUri, checksum: info.md5, byteSize: info.size };
    } catch (error) {
      await FileSystem.deleteAsync(stagingUri, { idempotent: true }).catch(() => undefined);
      throw error;
    }
  }

  #assertOwnedUri(uri: string): void {
    if (!uri.startsWith(this.#ownedDirectory)) {
      throw new Error("refusing to access a non-owned file");
    }
    const name = uri.slice(this.#ownedDirectory.length);
    if (name === "" || name.includes("/") || name.includes("\\")) {
      throw new Error("owned file URI is not a flat generated path");
    }
  }

  async remove(ownedUri: string): Promise<void> {
    this.#assertOwnedUri(ownedUri);
    await FileSystem.deleteAsync(ownedUri, { idempotent: true });
  }

  async listOrphans(): Promise<string[]> {
    await this.#ensureDirectories();
    return (await FileSystem.readDirectoryAsync(this.#ownedDirectory))
      .map((name) => `${this.#ownedDirectory}${name}`)
      .sort();
  }

  async exists(ownedUri: string): Promise<boolean> {
    this.#assertOwnedUri(ownedUri);
    const info = await FileSystem.getInfoAsync(ownedUri);
    return info.exists && !info.isDirectory;
  }

  async cleanupStaging(): Promise<number> {
    await this.#ensureDirectories();
    const names = await FileSystem.readDirectoryAsync(this.#stagingDirectory);
    for (const name of names) {
      await FileSystem.deleteAsync(`${this.#stagingDirectory}${name}`, { idempotent: true });
    }
    return names.length;
  }
}

// [Implementation 3-2]
// 선택한 파일을 앱 저장소로 옮기고 시작할 때 누락·미참조 파일을 정리합니다.
export class AttachmentStorageMaintenance {
  readonly #repository: SQLiteFieldNotesRepository;
  readonly #files: ExpoAttachmentFileStore;

  constructor(repository: SQLiteFieldNotesRepository, files: ExpoAttachmentFileStore) {
    this.#repository = repository;
    this.#files = files;
  }

  async reconcile(): Promise<{
    removedOrphanUris: string[];
    missingAttachmentIds: string[];
    stagingFilesRemoved: number;
  }> {
    // 파일 저장과 DB 갱신은 함께 커밋되지 않으므로 양쪽 목록을 비교해 어긋난 항목을 정리합니다.
    const [attachments, ownedUris, stagingFilesRemoved] = await Promise.all([
      this.#repository.listAttachments(),
      this.#files.listOrphans(),
      this.#files.cleanupStaging(),
    ]);
    const referenced = new Set(
      attachments
        .filter((attachment) => attachment.state !== "removed")
        .map((attachment) => attachment.localUri),
    );
    const removedOrphanUris: string[] = [];
    for (const uri of ownedUris) {
      if (referenced.has(uri)) continue;
      await this.#files.remove(uri);
      removedOrphanUris.push(uri);
    }

    const missingAttachmentIds: string[] = [];
    for (const attachment of attachments) {
      if (attachment.state === "removed") continue;
      let exists = false;
      try {
        exists = await this.#files.exists(attachment.localUri);
      } catch {
        exists = false;
      }
      if (exists) continue;
      await this.#repository.markAttachmentMissing(attachment.id);
      missingAttachmentIds.push(attachment.id);
    }
    return { removedOrphanUris, missingAttachmentIds, stagingFilesRemoved };
  }
}
