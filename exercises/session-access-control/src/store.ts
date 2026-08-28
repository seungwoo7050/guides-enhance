import { randomUUID } from "node:crypto";
import type { User } from "./contracts";

export interface SessionGrant {
  token: string;
  maxAgeSeconds: number;
}

export interface SecurityStore {
  findUserByHandle(handle: string): User | null;
  findUserById(id: string): User | null;
  listUsers(): User[];
  updateDisplayName(id: string, displayName: string): User | null;
  createSession(userId: string): SessionGrant;
  resolveSession(token: string): User | null;
  revokeSession(token: string): void;
}

// [Implementation 2] Per-app users and sessions
export class InMemorySecurityStore implements SecurityStore {
  private readonly users = new Map<string, User>([
    ["u-alpha", { id: "u-alpha", handle: "alpha", displayName: "알파", role: "user" }],
    ["u-admin", { id: "u-admin", handle: "admin", displayName: "관리자", role: "admin" }]
  ]);

  private readonly sessions = new Map<string, { userId: string; expiresAt: number }>();

  constructor(
    private readonly now: () => number = Date.now,
    private readonly sessionTtlSeconds = 60 * 60
  ) {
    if (!Number.isInteger(sessionTtlSeconds) || sessionTtlSeconds <= 0) {
      throw new RangeError("sessionTtlSeconds는 양의 정수여야 합니다.");
    }
  }

  findUserByHandle(handle: string): User | null {
    return this.clone([...this.users.values()].find((user) => user.handle === handle) ?? null);
  }

  findUserById(id: string): User | null {
    return this.clone(this.users.get(id) ?? null);
  }

  listUsers(): User[] {
    return [...this.users.values()].map((user) => ({ ...user }));
  }

  updateDisplayName(id: string, displayName: string): User | null {
    const current = this.users.get(id);
    if (!current) return null;
    const updated = { ...current, displayName };
    this.users.set(id, updated);
    return { ...updated };
  }

  createSession(userId: string): SessionGrant {
    const token = randomUUID();
    this.sessions.set(token, {
      userId,
      expiresAt: this.now() + this.sessionTtlSeconds * 1_000
    });
    return { token, maxAgeSeconds: this.sessionTtlSeconds };
  }

  resolveSession(token: string): User | null {
    const session = this.sessions.get(token);
    if (!session) return null;
    if (session.expiresAt <= this.now()) {
      this.sessions.delete(token);
      return null;
    }
    return this.findUserById(session.userId);
  }

  revokeSession(token: string): void {
    this.sessions.delete(token);
  }

  private clone(user: User | null): User | null {
    return user ? { ...user } : null;
  }
}
