import process from "node:process";
import { calculateDirectoryTreeEvidence } from "./directory-tree.ts";

const [path] = process.argv.slice(2);
if (!path) {
  console.error("usage: digest:directory-tree <directory>");
  process.exitCode = 2;
} else {
  console.log(JSON.stringify(await calculateDirectoryTreeEvidence(path), null, 2));
}
