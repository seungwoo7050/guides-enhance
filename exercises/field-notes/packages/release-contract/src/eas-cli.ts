import { readFile } from "node:fs/promises";
import process from "node:process";
import { validateEasConfiguration } from "./eas-profile.ts";

const [path] = process.argv.slice(2);
if (!path) {
  console.error("usage: validate:eas <eas.json>");
  process.exitCode = 2;
} else {
  const result = validateEasConfiguration(JSON.parse(await readFile(path, "utf8")));
  console.log(JSON.stringify(result, null, 2));
  if (!result.configurationValid) process.exitCode = 1;
}
