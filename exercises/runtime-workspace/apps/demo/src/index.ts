// [Implementation 4] Public package import
import { parsePort, sum } from "@runtime-workspace/math";

console.log("sum", sum([1, 2, 3]));
console.log("port", parsePort(process.env.PORT ?? "4000"));

// [Implementation 5] Event-loop observation
console.log("sync");
queueMicrotask(() => console.log("microtask"));
setTimeout(() => console.log("task"), 0);
