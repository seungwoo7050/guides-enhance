import { z } from "zod";

// [Implementation 1] Memo request schema
export const CreateMemoSchema = z.object({
  title: z.string().trim().min(1).max(80),
  body: z.string().trim().max(500).default("")
});

export type CreateMemoInput = z.infer<typeof CreateMemoSchema>;
export interface Memo { id: string; title: string; body: string }
