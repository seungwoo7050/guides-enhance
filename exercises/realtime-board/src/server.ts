import { buildApp } from "./app";

// [Implementation 10] Network entry point
const port = parsePort(process.env.PORT ?? "4000");
await (await buildApp()).listen({ host: "0.0.0.0", port });

function parsePort(value: string): number {
  const port = Number(value);
  if (!Number.isInteger(port) || port < 1 || port > 65_535) {
    throw new Error("PORT는 1부터 65535 사이의 정수여야 합니다.");
  }
  return port;
}
