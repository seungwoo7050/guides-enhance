import { buildApp } from "./app.js";
import { MemoryMemoRepository } from "./repository.js";

// [Implementation 7] Network entry point
const app = buildApp(new MemoryMemoRepository());
await app.listen({ host: "0.0.0.0", port: 4000 });
