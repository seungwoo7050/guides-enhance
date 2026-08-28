// [Implementation 2] Abortable search adapter
export interface User { id: string; handle: string; displayName: string }

const users: User[] = [
  { id: "u1", handle: "alpha", displayName: "알파" },
  { id: "u2", handle: "beta", displayName: "베타" },
  { id: "u3", handle: "gamma", displayName: "감마" }
];

export async function searchUsers(query: string, signal: AbortSignal): Promise<User[]> {
  signal.throwIfAborted();
  await new Promise<void>((resolve, reject) => {
    const timer = setTimeout(resolve, query === "a" ? 500 : 150);
    const onAbort = () => {
      clearTimeout(timer);
      reject(new DOMException("aborted", "AbortError"));
    };
    signal.addEventListener("abort", onAbort, { once: true });
  });
  if (query === "error") throw new Error("의도적으로 발생시킨 검색 오류입니다.");
  const normalized = query.trim().toLowerCase();
  return normalized
    ? users.filter((user) => `${user.handle} ${user.displayName}`.toLowerCase().includes(normalized))
    : users;
}
