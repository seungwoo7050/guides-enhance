import assert from "node:assert/strict";
import { mkdir, mkdtemp, rm, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { calculateDirectoryTreeEvidence } from "../src/directory-tree.ts";

test("produces a stable canonical digest for files, directories, modes, and symlinks", async (context) => {
  const root = await mkdtemp(join(tmpdir(), "field-notes-tree-"));
  context.after(() => rm(root, { recursive: true, force: true }));
  await mkdir(join(root, "Payload"));
  await writeFile(join(root, "Payload", "app"), "binary");
  await symlink("Payload/app", join(root, "current"));

  const first = await calculateDirectoryTreeEvidence(root);
  const second = await calculateDirectoryTreeEvidence(root);
  assert.equal(first.treeSha256, second.treeSha256);
  assert.equal(first.fileCount, 1);
  assert.equal(first.byteSize, 6);
  assert(first.canonicalManifest.includes("F "));
  assert(first.canonicalManifest.includes("L "));
});
