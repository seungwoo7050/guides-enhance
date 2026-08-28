import type { CreateMemoInput } from "./contracts.js";
import type { MemoRepository } from "./repository.js";

// [Implementation 3] Duplicate-title rule
export class ConflictError extends Error {}

export async function createMemo(repo: MemoRepository, input: CreateMemoInput) {
  if (await repo.findByTitle(input.title)) throw new ConflictError("title_taken");
  return repo.create(input);
}
