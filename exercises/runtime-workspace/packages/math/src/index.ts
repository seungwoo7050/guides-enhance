// [Implementation 2] Pure sum operation
export function sum(values: readonly number[]): number {
  return values.reduce((total, value) => total + value, 0);
}

// [Implementation 3] TCP port parsing
export function parsePort(input: unknown): number {
  const value = typeof input === "string" ? Number(input) : input;
  if (typeof value !== "number" || !Number.isInteger(value) || value < 1 || value > 65535) {
    throw new Error("포트는 1부터 65535 사이의 정수여야 합니다.");
  }
  return value;
}
