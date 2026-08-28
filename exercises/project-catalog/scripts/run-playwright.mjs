import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { createServer } from "node:net";
import path from "node:path";

const host = "127.0.0.1";

// [Implementation 15-1]
// 사용 가능한 포트를 골라 Playwright에 넘기고, 하위 프로세스의 종료 상태를 그대로 반환합니다.
const port = await findAvailablePort();
const forwarded = process.argv.slice(2);
const cli = resolvePackageBinary("@playwright/test", "playwright");
const result = spawnSync(process.execPath, [cli, "test", ...forwarded], {
  stdio: "inherit",
  env: {
    ...process.env,
    CATALOG_E2E_PORT: String(port)
  }
});

if (result.error) {
  console.error(`Playwright launch failed: ${result.error.message}`);
  process.exit(1);
}
if (result.signal) {
  console.error(`Playwright exited after signal ${result.signal}.`);
  process.exit(1);
}
process.exit(result.status ?? 1);

function resolvePackageBinary(packageName, binaryName) {
  const require = createRequire(import.meta.url);
  const packagePath = require.resolve(`${packageName}/package.json`);
  const metadata = JSON.parse(readFileSync(packagePath, "utf8"));
  const relative =
    typeof metadata.bin === "string" ? metadata.bin : metadata.bin?.[binaryName];
  if (typeof relative !== "string") {
    throw new Error(`${packageName} does not expose the ${binaryName} binary.`);
  }
  return path.resolve(path.dirname(packagePath), relative);
}

async function findAvailablePort() {
  const server = createServer();
  server.unref();
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, host, resolve);
  });
  const address = server.address();
  if (typeof address !== "object" || address === null) {
    server.close();
    throw new Error("Could not determine an available Playwright port.");
  }
  const selected = address.port;
  await new Promise((resolve, reject) =>
    server.close((error) => (error ? reject(error) : resolve()))
  );
  return selected;
}
