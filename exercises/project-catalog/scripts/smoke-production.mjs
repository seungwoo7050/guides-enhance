import { spawn } from "node:child_process";
import { randomUUID } from "node:crypto";
import { once } from "node:events";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { createServer } from "node:net";
import path from "node:path";
import { setTimeout as delay } from "node:timers/promises";
import { fileURLToPath } from "node:url";

const projectRoot = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const host = "127.0.0.1";
const maximumOutput = 64 * 1024;

await main().catch((error) => {
  console.error(formatError(error));
  process.exitCode = 1;
});

// [Implementation 16]
// 운영 서버를 직접 띄워 health, HTML, API, 비밀값 비노출과 프로세스 정리를 확인합니다.
async function main() {
  const port = await findAvailablePort();
  const baseURL = `http://${host}:${port}`;
  const release = `smoke-${randomUUID()}`;
  const secretCanary = `server-only-${randomUUID()}`;
  const nextCli = resolvePackageBinary("next", "next");
  let child;
  let primaryFailure;
  let cleanupFailure;
  let output = "";
  let launchFailure;

  try {
    child = spawn(
      process.execPath,
      [nextCli, "start", "--hostname", host, "--port", String(port)],
      {
        cwd: projectRoot,
        detached: process.platform !== "win32",
        env: {
          ...process.env,
          NODE_ENV: "production",
          APP_RELEASE: release,
          CATALOG_SERVER_ONLY_CANARY: secretCanary
        },
        stdio: ["ignore", "pipe", "pipe"]
      }
    );
    child.once("error", (error) => {
      launchFailure = error;
    });
    child.stdout?.on("data", (chunk) => {
      output = appendBounded(output, String(chunk));
    });
    child.stderr?.on("data", (chunk) => {
      output = appendBounded(output, String(chunk));
    });

    await waitForHealth({
      baseURL,
      child,
      getLaunchFailure: () => launchFailure,
      getOutput: () => output
    });
    await verifyHealth(baseURL, release, secretCanary);

    const html = await fetchText(`${baseURL}/`, 3_000);
    if (!/<h1[^>]*>Project Catalog<\/h1>/.test(html)) {
      throw new Error("The root HTML does not contain the Project Catalog heading.");
    }
    assertSecretAbsent(html, secretCanary, "root HTML");

    const search = await fetchJson(`${baseURL}/api/projects?page=1`, 3_000);
    if (
      typeof search !== "object" ||
      search === null ||
      !("projects" in search) ||
      !Array.isArray(search.projects)
    ) {
      throw new Error("The project API does not satisfy its minimum search contract.");
    }
    assertSecretAbsent(JSON.stringify(search), secretCanary, "project API");

    const scripts = extractScriptSources(html);
    if (scripts.length === 0) {
      throw new Error("The initial HTML does not reference a JavaScript artifact.");
    }
    for (const source of scripts) {
      const script = await fetchText(new URL(source, baseURL).toString(), 3_000);
      assertSecretAbsent(script, secretCanary, `JavaScript artifact ${source}`);
    }

    console.log(`Production smoke passed: ${baseURL} (${release})`);
  } catch (error) {
    primaryFailure = withServerOutput(error, output);
  } finally {
    try {
      if (child) await stopChildTree(child);
    } catch (error) {
      cleanupFailure = withServerOutput(error, output);
    }
  }

  if (primaryFailure && cleanupFailure) {
    throw new AggregateError(
      [primaryFailure, cleanupFailure],
      "Production verification and process cleanup both failed."
    );
  }
  if (primaryFailure) throw primaryFailure;
  if (cleanupFailure) throw cleanupFailure;
}

async function waitForHealth({ baseURL, child, getLaunchFailure, getOutput }) {
  const deadline = Date.now() + 20_000;
  while (Date.now() < deadline) {
    const launchFailure = getLaunchFailure();
    if (launchFailure) {
      throw new Error(`Production server launch failed: ${launchFailure.message}`);
    }
    if (hasExited(child)) {
      throw new Error(
        `Production server exited before readiness. code=${child.exitCode} signal=${child.signalCode}\n${getOutput()}`
      );
    }
    try {
      const response = await fetchWithTimeout(`${baseURL}/api/health`, {}, 1_000);
      if (response.ok) return;
    } catch {
      // 서버가 준비되는 동안의 연결 거부와 시간 초과는 다음 확인에서 다시 시도합니다.
    }
    await delay(100);
  }
  throw new Error(`Production server was not ready before the deadline.\n${getOutput()}`);
}

async function verifyHealth(baseURL, release, secretCanary) {
  const response = await fetchWithTimeout(`${baseURL}/api/health`, {}, 3_000);
  if (!response.ok) throw new Error(`Health request failed: ${response.status}`);
  const body = await response.json();
  const keys = Object.keys(body).sort();
  if (keys.join(",") !== "release,status") {
    throw new Error(`Health exposes unexpected fields: ${keys.join(",")}`);
  }
  if (body.status !== "ok" || body.release !== release) {
    throw new Error("Health status or release does not match the running process.");
  }
  const cacheControl = response.headers.get("cache-control") ?? "";
  if (!cacheControl.toLocaleLowerCase().includes("no-store")) {
    throw new Error("Health does not include Cache-Control: no-store.");
  }
  assertSecretAbsent(JSON.stringify(body), secretCanary, "health response");
}

async function fetchText(url, timeout) {
  const response = await fetchWithTimeout(url, {}, timeout);
  if (!response.ok) throw new Error(`${url} failed: ${response.status}`);
  return response.text();
}

async function fetchJson(url, timeout) {
  const response = await fetchWithTimeout(url, {}, timeout);
  if (!response.ok) throw new Error(`${url} failed: ${response.status}`);
  return response.json();
}

function fetchWithTimeout(url, init, timeout) {
  return fetch(url, { ...init, signal: AbortSignal.timeout(timeout) });
}

function extractScriptSources(html) {
  const sources = [];
  for (const match of html.matchAll(/<script[^>]+src=["']([^"']+\.js(?:\?[^"']*)?)["'][^>]*>/g)) {
    sources.push(match[1].replaceAll("&amp;", "&"));
  }
  return [...new Set(sources)];
}

function assertSecretAbsent(content, secret, label) {
  if (content.includes(secret)) {
    throw new Error(`${label} exposes the server-only secret.`);
  }
}

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
    throw new Error("Could not determine an available TCP port.");
  }
  const port = address.port;
  await new Promise((resolve, reject) =>
    server.close((error) => (error ? reject(error) : resolve()))
  );
  return port;
}

// Unix에서는 프로세스 그룹에 신호를 보내 실행 래퍼와 하위 서버를 함께 종료합니다.
async function stopChildTree(child) {
  if (!child.pid || hasExited(child)) return;
  sendSignal(child, "SIGTERM");
  if (await waitForExit(child, 2_000)) return;
  sendSignal(child, "SIGKILL");
  if (await waitForExit(child, 2_000)) return;
  throw new Error(`Production server process did not exit: pid=${child.pid}`);
}

function sendSignal(child, signal) {
  if (!child.pid || hasExited(child)) return;
  try {
    if (process.platform !== "win32") process.kill(-child.pid, signal);
    else child.kill(signal);
  } catch (error) {
    if (error?.code !== "ESRCH") throw error;
  }
}

async function waitForExit(child, timeout) {
  if (hasExited(child)) return true;
  await Promise.race([once(child, "exit"), delay(timeout)]);
  return hasExited(child);
}

function hasExited(child) {
  return child.exitCode !== null || child.signalCode !== null;
}

function appendBounded(current, addition) {
  const next = current + addition;
  return next.length <= maximumOutput ? next : next.slice(next.length - maximumOutput);
}

function withServerOutput(error, output) {
  const message = error instanceof Error ? error.message : String(error);
  const wrapped = new Error(
    output ? `${message}\n--- production server output ---\n${output}` : message
  );
  if (error instanceof Error && error.stack) {
    wrapped.stack = `${wrapped.stack}\nCaused by:\n${error.stack}`;
  }
  return wrapped;
}

function formatError(error) {
  if (error instanceof AggregateError) {
    return [error.message, ...error.errors.map((entry) => formatError(entry))].join("\n\n");
  }
  return error instanceof Error ? error.stack ?? error.message : String(error);
}
