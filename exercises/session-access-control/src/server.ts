import { buildApp } from "./app";
import { InMemorySecurityStore } from "./store";

// [Implementation 10] Network entry point
const port = parsePort(process.env.PORT ?? "4000");
const origins = (process.env.ALLOWED_ORIGINS ?? "http://localhost:3000")
  .split(",")
  .map((origin) => origin.trim())
  .filter(Boolean);

if (origins.length === 0) throw new Error("ALLOWED_ORIGINS에는 하나 이상의 origin이 필요합니다.");

await buildApp({
  store: new InMemorySecurityStore(),
  allowedOrigins: origins
}).listen({ host: "0.0.0.0", port });

function parsePort(value: string): number {
  const port = Number(value);
  if (!Number.isInteger(port) || port < 1 || port > 65_535) {
    throw new Error("PORT는 1부터 65535 사이의 정수여야 합니다.");
  }
  return port;
}
