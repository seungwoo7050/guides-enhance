import { spawn, spawnSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { once } from "node:events";
import { readFile, readdir, rm, stat } from "node:fs/promises";
import { createServer } from "node:net";
import path from "node:path";
import { setTimeout as delay } from "node:timers/promises";
import { fileURLToPath } from "node:url";

const projectRoot = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const dist = path.join(projectRoot, "dist");
const host = "127.0.0.1";
const maximumOutput = 64 * 1024;

// [Implementation 14]
// Smoke rebuilds with a private canary, inspects dist, serves it, then guarantees process cleanup.
await main().catch((error) => {
  console.error(formatError(error));
  process.exitCode = 1;
});

async function main() {
  const privateCanary = `private-${randomUUID()}`;
  await rm(dist, { recursive: true, force: true });
  runBuild(privateCanary);
  await verifyFiles(privateCanary);

  const port = await findAvailablePort();
  const baseURL = `http://${host}:${port}`;
  let child;
  let output = "";
  let launchFailure;
  let primaryFailure;
  let cleanupFailure;

  try {
    child = spawn("npm", ["run", "preview", "--", "--host", host, "--port", String(port)], {
      cwd: projectRoot,
      detached: process.platform !== "win32",
      env: {
        ...process.env,
        ASTRO_PREVIEW_BACKGROUND: "0",
        PUBLIC_BUILD_LABEL: "smoke"
      },
      stdio: ["ignore", "pipe", "pipe"]
    });
    child.once("error", (error) => {
      launchFailure = error;
    });
    child.stdout?.on("data", (chunk) => {
      output = appendBounded(output, String(chunk));
    });
    child.stderr?.on("data", (chunk) => {
      output = appendBounded(output, String(chunk));
    });

    await waitForPreview(baseURL, child, () => launchFailure, () => output);
    await verifyResponse(baseURL);
    console.log(`static smoke 통과: ${baseURL}`);
  } catch (error) {
    primaryFailure = withOutput(error, output);
  } finally {
    try {
      if (child) await stopChildTree(child);
    } catch (error) {
      cleanupFailure = withOutput(error, output);
    }
  }

  if (primaryFailure && cleanupFailure) {
    throw new AggregateError([primaryFailure, cleanupFailure], "smoke와 process 정리가 모두 실패했습니다.");
  }
  if (primaryFailure) throw primaryFailure;
  if (cleanupFailure) throw cleanupFailure;
}

function runBuild(privateCanary) {
  const result = spawnSync("npm", ["run", "build"], {
    cwd: projectRoot,
    stdio: "inherit",
    env: {
      ...process.env,
      RESOURCE_DIRECTORY_PRIVATE_CANARY: privateCanary,
      PUBLIC_BUILD_LABEL: "smoke"
    }
  });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`Astro build 실패: ${result.status}`);
}

async function verifyFiles(privateCanary) {
  const expected = [
    "index.html",
    "404.html",
    "resources/index.html",
    "resources/http-status-reference/index.html",
    "categories/web/index.html",
    "resources.json"
  ];
  for (const relative of expected) {
    const target = path.join(dist, relative);
    const metadata = await stat(target).catch(() => null);
    if (!metadata?.isFile()) throw new Error(`필수 build 파일이 없습니다: ${relative}`);
  }

  const resources = JSON.parse(await readFile(path.join(dist, "resources.json"), "utf8"));
  if (!Array.isArray(resources) || resources.length !== 6) {
    throw new Error("resources.json의 공개 자료 수가 예상과 다릅니다.");
  }
  const keys = Object.keys(resources[0]).sort();
  if (keys.join(",") !== "category,categoryLabel,featured,id,publishedAt,summary,tags,title,updatedAt") {
    throw new Error(`resources.json 공개 필드가 달라졌습니다: ${keys.join(",")}`);
  }

  for (const file of await collectFiles(dist)) {
    const content = await readFile(file);
    if (content.includes(Buffer.from(privateCanary))) {
      throw new Error(`private canary가 build 결과에 포함되었습니다: ${path.relative(dist, file)}`);
    }
  }
}

async function verifyResponse(baseURL) {
  const home = await fetchText(`${baseURL}/`);
  if (!home.includes("필요할 때 다시 찾을 수 있는 기술 자료")) {
    throw new Error("홈 HTML에서 핵심 제목을 찾지 못했습니다.");
  }
  if (home.includes("<astro-island")) {
    throw new Error("홈 route에 client island가 포함되었습니다.");
  }

  const detail = await fetchText(`${baseURL}/resources/http-status-reference/`);
  if ((detail.match(/<astro-island/g) ?? []).length !== 1) {
    throw new Error("상세 route의 island 수가 1개가 아닙니다.");
  }

  const response = await fetch(`${baseURL}/resources.json`, { signal: AbortSignal.timeout(3_000) });
  if (!response.ok) throw new Error(`resources.json 응답 실패: ${response.status}`);
  const resources = await response.json();
  if (!Array.isArray(resources) || resources.length !== 6) {
    throw new Error("preview의 resources.json 응답이 올바르지 않습니다.");
  }
}

async function waitForPreview(baseURL, child, getLaunchFailure, getOutput) {
  const deadline = Date.now() + 20_000;
  while (Date.now() < deadline) {
    const launchError = getLaunchFailure();
    if (launchError) throw new Error(`preview 실행 실패: ${launchError.message}`);
    if (child.exitCode !== null || child.signalCode !== null) {
      throw new Error(`preview가 준비되기 전에 종료되었습니다.
${getOutput()}`);
    }
    try {
      const response = await fetch(baseURL, { signal: AbortSignal.timeout(1_000) });
      if (response.ok) return;
    } catch {
      // Preview has not bound the selected port yet.
    }
    await delay(100);
  }
  throw new Error(`preview가 제한 시간 안에 준비되지 않았습니다.
${getOutput()}`);
}

async function fetchText(url) {
  const response = await fetch(url, { signal: AbortSignal.timeout(3_000) });
  if (!response.ok) throw new Error(`${url} 응답 실패: ${response.status}`);
  return response.text();
}

async function collectFiles(directory) {
  const result = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) result.push(...(await collectFiles(target)));
    else if (entry.isFile()) result.push(target);
  }
  return result;
}

async function findAvailablePort() {
  const server = createServer();
  server.unref();
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, host, resolve);
  });
  const address = server.address();
  if (typeof address !== "object" || address === null) throw new Error("포트를 찾지 못했습니다.");
  const port = address.port;
  await new Promise((resolve, reject) => server.close((error) => (error ? reject(error) : resolve())));
  return port;
}

async function stopChildTree(child) {
  if (!child.pid || child.exitCode !== null || child.signalCode !== null) return;
  sendSignal(child.pid, "SIGTERM");
  if (await waitForExit(child, 2_000)) return;
  sendSignal(child.pid, "SIGKILL");
  if (await waitForExit(child, 2_000)) return;
  throw new Error(`preview process가 종료되지 않았습니다: pid=${child.pid}`);
}

function sendSignal(pid, signal) {
  try {
    if (process.platform === "win32") process.kill(pid, signal);
    else process.kill(-pid, signal);
  } catch (error) {
    if (error?.code !== "ESRCH") throw error;
  }
}

async function waitForExit(child, timeout) {
  if (child.exitCode !== null || child.signalCode !== null) return true;
  await Promise.race([once(child, "exit"), delay(timeout)]);
  return child.exitCode !== null || child.signalCode !== null;
}

function appendBounded(current, addition) {
  const next = current + addition;
  return next.length <= maximumOutput ? next : next.slice(-maximumOutput);
}

function withOutput(error, output) {
  const message = error instanceof Error ? error.message : String(error);
  return new Error(output ? `${message}
--- preview output ---
${output}` : message);
}

function formatError(error) {
  if (error instanceof AggregateError) {
    return [error.message, ...error.errors.map(formatError)].join("\n\n");
  }
  return error instanceof Error ? error.stack ?? error.message : String(error);
}
