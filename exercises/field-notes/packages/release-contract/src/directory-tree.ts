import { createHash } from "node:crypto";
import { lstat, readFile, readdir, readlink } from "node:fs/promises";
import { basename, join, relative, sep } from "node:path";

export type DirectoryTreeEvidence = {
  directoryName: string;
  fileCount: number;
  byteSize: number;
  treeDigestAlgorithm: "sha256-canonical-tree-v1";
  treeSha256: string;
  canonicalManifest: string;
};

function sha256(value: string | Uint8Array): string {
  return createHash("sha256").update(value).digest("hex");
}

function mode(value: number): string {
  return (value & 0o7777).toString(8).padStart(4, "0");
}

function utf8Length(value: string): number {
  return Buffer.byteLength(value, "utf8");
}

function posixPath(root: string, path: string): string {
  return relative(root, path).split(sep).join("/");
}

export async function calculateDirectoryTreeEvidence(
  root: string,
): Promise<DirectoryTreeEvidence> {
  const rootStat = await lstat(root);
  if (!rootStat.isDirectory() || rootStat.isSymbolicLink()) {
    throw new Error("root must be a real directory");
  }

  const entries: string[] = [];
  async function walk(directory: string): Promise<void> {
    const children = await readdir(directory, { withFileTypes: true });
    for (const child of children) {
      const path = join(directory, child.name);
      entries.push(path);
      if (child.isDirectory()) await walk(path);
    }
  }
  await walk(root);
  entries.sort((left, right) => Buffer.from(posixPath(root, left)).compare(Buffer.from(posixPath(root, right))));

  const records = [`D ${mode(rootStat.mode)} 0:`];
  let fileCount = 0;
  let byteSize = 0;

  for (const path of entries) {
    const stat = await lstat(path);
    const name = posixPath(root, path);
    const pathLength = utf8Length(name);
    if (stat.isDirectory()) {
      records.push(`D ${mode(stat.mode)} ${pathLength}:${name}`);
    } else if (stat.isFile()) {
      const data = await readFile(path);
      fileCount += 1;
      byteSize += data.byteLength;
      records.push(`F ${mode(stat.mode)} ${pathLength}:${name} ${data.byteLength} ${sha256(data)}`);
    } else if (stat.isSymbolicLink()) {
      const target = await readlink(path);
      records.push(`L ${mode(stat.mode)} ${pathLength}:${name} ${utf8Length(target)}:${target}`);
    } else {
      throw new Error(`unsupported special file: ${name}`);
    }
  }

  const canonicalManifest = `${records.join("\n")}\n`;
  return {
    directoryName: basename(root),
    fileCount,
    byteSize,
    treeDigestAlgorithm: "sha256-canonical-tree-v1",
    treeSha256: sha256(canonicalManifest),
    canonicalManifest,
  };
}
