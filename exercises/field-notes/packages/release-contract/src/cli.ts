import { readFile } from "node:fs/promises";
import process from "node:process";
import { validateReleasePair } from "./validate.ts";

async function readJson(path: string): Promise<unknown> {
  return JSON.parse(await readFile(path, "utf8"));
}

const [androidPath, iosPath] = process.argv.slice(2);
if (!androidPath || !iosPath) {
  console.error("usage: validate:release <android-manifest.json> <ios-manifest.json>");
  process.exitCode = 2;
} else {
  const result = validateReleasePair(await readJson(androidPath), await readJson(iosPath));
  console.log(JSON.stringify(result, null, 2));
  if (!result.consistent) process.exitCode = 1;
}
