import { readFile } from "node:fs/promises";
import { sql } from "kysely";
import { createDb } from "./db.js";

// [Implementation 3] Migration runner cleanup
const db = createDb();
try {
  const source = await readFile(new URL("../migrations/001_initial.sql", import.meta.url), "utf8");
  await sql.raw(source).execute(db);
  console.log("마이그레이션을 적용했습니다.");
} finally {
  await db.destroy();
}
