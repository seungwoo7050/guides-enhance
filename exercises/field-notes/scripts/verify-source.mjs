import { access, readFile, readdir } from "node:fs/promises";
import { constants } from "node:fs";
import { dirname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import process from "node:process";

const rootPath = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const forbiddenSegments = new Set([
  "skeleton",
  "workspace",
  "reference",
  "specs",
  "checks",
  "solution",
  "answers",
]);
const ignoredDirectories = new Set([
  "node_modules",
  ".git",
  "dist",
  ".expo",
  "android",
  "ios",
  "coverage",
]);

const implementationOrder = [
  ["0", "프로세스가 사용할 저장소·파일·기기 기능·동기화 서비스를 생성합니다", "apps/mobile/src/application/FieldNotesRuntime.tsx"],
  ["1", "기록·첨부 파일·outbox·충돌·화면 이동 상태를 정의합니다", "packages/core/src/contracts.ts"],
  ["1-1", "저장소·파일·기기 API·세션·동기화 전송 호출 형식을 정의합니다", "packages/core/src/ports.ts"],
  ["2", "화면 이동 입력을 검증하고 중복 요청을 거른 뒤 안전한 경로를 선택합니다", "packages/core/src/navigation.ts"],
  ["3", "프로세스 재시작 뒤 복원할 SQLite 테이블을 만들고 마이그레이션합니다", "apps/mobile/src/storage/SQLiteFieldNotesRepository.ts"],
  ["3-1", "기록 변경과 outbox 명령 추가를 하나의 트랜잭션으로 커밋합니다", "apps/mobile/src/storage/SQLiteFieldNotesRepository.ts"],
  ["3-2", "선택한 파일을 앱 저장소로 옮기고 시작할 때 누락·미참조 파일을 정리합니다", "apps/mobile/src/storage/attachment-files.ts"],
  ["4", "카메라·사진 선택기·위치·권한·중단 결과를 앱이 처리할 상태로 변환합니다", "packages/core/src/device-coordinator.ts"],
  ["5", "각 명령을 한 번만 적용하고 원격 처리 실패를 결정적으로 재현합니다", "packages/fault-server/src/server.ts"],
  ["6", "명령의 최초 시도 사본·lease·재시도·처리 결과·충돌을 저장합니다", "packages/sync-engine/src/repository.ts"],
  ["6-1", "처리 결과를 기록하기 전에 응답 ID·버전·필수 값을 검증합니다", "packages/sync-engine/src/response-parser.ts"],
  ["6-2", "제한 시간 안에 명령을 가져오고 결과를 모르는 요청은 같은 명령으로 재시도합니다", "packages/sync-engine/src/worker.ts"],
  ["6-3", "새 명령으로 충돌을 해결하고 아직 보내지 않은 명령만 새 기준 버전으로 바꿉니다", "packages/sync-engine/src/repository.ts"],
  ["7", "제한 시간형 동기화 작업자를 SQLite 저장소와 HTTP 전송에 연결합니다", "apps/mobile/src/sync/production-sync.ts"],
  ["8", "수동·앱 활성화·백그라운드·알림 실행에서 같은 동기화 작업자를 호출합니다", "packages/lifecycle-engine/src/sync-coordinator.ts"],
  ["8-1", "알림 ID를 먼저 저장하고 현재 저장 상태를 조회해 이동할 화면을 정합니다", "packages/lifecycle-engine/src/notification.ts"],
  ["8-2", "Android 알림 채널 생성·권한 확인·푸시 토큰 요청 순서를 고정합니다", "packages/lifecycle-engine/src/android-registration.ts"],
  ["8-3", "오래된 로그아웃이 새 계정을 지우지 않도록 설치·계정·토큰 연결을 갱신합니다", "packages/lifecycle-engine/src/installation-coordinator.ts"],
  ["9", "화면에서 저장·사진·동기화·백그라운드·알림 기능을 호출할 수 있게 제공합니다", "apps/mobile/src/application/FieldNotesRuntime.tsx"],
  ["10", "EAS 빌드 프로필과 Android·iOS 릴리스 후보 근거가 서로 일치하는지 검증합니다", "packages/release-contract/src/validate.ts"],
  ["11", "서로 모순되는 릴리스 근거를 거부하고 프로젝트 전체 불변식을 회귀 테스트로 확인합니다", "packages/release-contract/tests/release-contract.test.ts"],
];

async function walk(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  entries.sort((left, right) => left.name.localeCompare(right.name));
  const files = [];
  for (const entry of entries) {
    if (entry.isDirectory() && ignoredDirectories.has(entry.name)) continue;
    const path = join(directory, entry.name);
    if (entry.isDirectory()) files.push(...await walk(path));
    else files.push(path);
  }
  return files;
}

function portablePath(path) {
  return relative(rootPath, path).split(sep).join("/");
}

function compareOrder(left, right) {
  const a = left.split("-").map(Number);
  const b = right.split("-").map(Number);
  for (let index = 0; index < Math.max(a.length, b.length); index += 1) {
    const difference = (a[index] ?? -1) - (b[index] ?? -1);
    if (difference !== 0) return difference;
  }
  return 0;
}

const files = await walk(rootPath);
const paths = files.map(portablePath);
const failures = [];

for (const path of paths) {
  for (const segment of path.split("/")) {
    if (forbiddenSegments.has(segment)) {
      failures.push(`${path}: obsolete educational segment '${segment}'`);
    }
  }
}

if (!paths.includes("README.md")) failures.push("README.md: missing standalone project README");

const readmes = paths.filter((path) => path.endsWith("README.md"));
for (const path of readmes) {
  const text = await readFile(join(rootPath, path), "utf8");
  for (const phrase of [
    "complete the skeleton",
    "learner workspace",
    "expected answer",
    "reference answer",
    "initial test should fail",
  ]) {
    if (text.toLowerCase().includes(phrase)) {
      failures.push(`${path}: educational phrase '${phrase}'`);
    }
  }
}

const sourceFiles = paths.filter((path) => /\.(?:ts|tsx|js|mjs)$/.test(path));
const annotations = [];
const annotationPattern = /\/\/ \[Implementation ([0-9]+(?:-[0-9]+)?)\]\r?\n\s*\/\/ ([^\r\n]+)\.?/g;
for (const path of sourceFiles) {
  const text = await readFile(join(rootPath, path), "utf8");
  for (const match of text.matchAll(annotationPattern)) {
    annotations.push({
      order: match[1],
      responsibility: match[2].replace(/\.$/, ""),
      path,
    });
  }
}
annotations.sort((left, right) => compareOrder(left.order, right.order));

if (annotations.length !== implementationOrder.length) {
  failures.push(`Implementation annotation count differs: expected=${implementationOrder.length} actual=${annotations.length}`);
}

for (const [order, responsibility, anchor] of implementationOrder) {
  const matching = annotations.filter((annotation) => annotation.order === order);
  if (matching.length !== 1) {
    failures.push(`Implementation ${order}: expected exactly one source annotation, found ${matching.length}`);
    continue;
  }
  const annotation = matching[0];
  if (annotation.responsibility !== responsibility) {
    failures.push(`Implementation ${order}: responsibility differs: '${annotation.responsibility}'`);
  }
  if (annotation.path !== anchor) {
    failures.push(`Implementation ${order}: anchor differs: '${annotation.path}'`);
  }
}

const readmePath = join(rootPath, "README.md");
let readme = "";
try {
  readme = await readFile(readmePath, "utf8");
} catch {
  // README 누락 오류는 위에서 이미 추가했습니다.
}
for (const [order, responsibility, anchor] of implementationOrder) {
  const row = `| \`${order}\` | ${responsibility} | \`${anchor}\` |`;
  if (!readme.includes(row)) failures.push(`README.md: missing exact Implementation ${order} table row`);
  try {
    await access(join(rootPath, anchor), constants.R_OK);
  } catch {
    failures.push(`Implementation ${order}: unreadable primary anchor '${anchor}'`);
  }
}

for (const path of sourceFiles) {
  const text = await readFile(join(rootPath, path), "utf8");
  for (const match of text.matchAll(/(?:from\s+|import\s*\()(["'])([^"']+)\1/g)) {
    const specifier = match[2];
    if (!specifier.startsWith(".")) continue;
    const target = resolve(dirname(join(rootPath, path)), specifier);
    if (target !== rootPath && !target.startsWith(`${rootPath}${sep}`)) {
      failures.push(`${path}: relative import escapes the standalone project: '${specifier}'`);
    }
  }
}

for (const path of paths.filter((value) => value.endsWith("package.json"))) {
  try {
    JSON.parse(await readFile(join(rootPath, path), "utf8"));
  } catch (error) {
    failures.push(`${path}: invalid JSON: ${error instanceof Error ? error.message : String(error)}`);
  }
}

if (failures.length > 0) {
  console.error(failures.join("\n"));
  process.exitCode = 1;
} else {
  console.log(`source verification passed: ${paths.length} files, ${annotations.length} implementation anchors`);
}
