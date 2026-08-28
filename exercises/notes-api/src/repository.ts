import { randomUUID } from "node:crypto";
import type { CreateMemoInput, Memo } from "./contracts.js";

// [Implementation 2] Memo persistence API
export interface MemoRepository {
  list(): Promise<Memo[]>;
  find(id: string): Promise<Memo | null>;
  findByTitle(title: string): Promise<Memo | null>;
  create(input: CreateMemoInput): Promise<Memo>;
}

export class MemoryMemoRepository implements MemoRepository {
  private readonly rows = new Map<string, Memo>();

  async list() { return [...this.rows.values()].map((row) => ({ ...row })); }
  async find(id: string) {
    const row = this.rows.get(id);
    return row ? { ...row } : null;
  }
  async findByTitle(title: string) {
    const row = [...this.rows.values()].find((candidate) => candidate.title === title);
    return row ? { ...row } : null;
  }
  async create(input: CreateMemoInput) {
    const row = { id: randomUUID(), ...input };
    this.rows.set(row.id, { ...row });
    return { ...row };
  }
}
