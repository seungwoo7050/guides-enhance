import cookie from "@fastify/cookie";
import cors from "@fastify/cors";
import Fastify, { type FastifyReply, type FastifyRequest } from "fastify";

import { LoginSchema, ProfileSchema, type User } from "./contracts";
import type { SecurityStore } from "./store";

const SESSION_COOKIE = "access_session";
const STATE_CHANGING_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export interface AppOptions {
  store: SecurityStore;
  allowedOrigins?: readonly string[];
  production?: boolean;
}

// [Implementation 3] Fastify plugins and injected store
export function buildApp({
  store,
  allowedOrigins = ["http://localhost:3000"],
  production = process.env.NODE_ENV === "production"
}: AppOptions) {
  const app = Fastify({ logger: false });
  const originSet = new Set(allowedOrigins);

  app.register(cors, { origin: [...originSet], credentials: true });
  app.register(cookie);

  // [Implementation 4] Exact Origin check before mutation
  app.addHook("preHandler", async (request, reply) => {
    if (!STATE_CHANGING_METHODS.has(request.method)) return;
    const origin = request.headers.origin;
    if (origin && !originSet.has(origin)) {
      return reply.code(403).send({ code: "origin_forbidden" });
    }
    if (request.cookies[SESSION_COOKIE] && !origin) {
      return reply.code(403).send({ code: "origin_forbidden" });
    }
  });

  // [Implementation 5] Session-token identity lookup
  function currentUser(request: FastifyRequest): User | null {
    const token = request.cookies[SESSION_COOKIE];
    return token ? store.resolveSession(token) : null;
  }

  function requireUser(request: FastifyRequest, reply: FastifyReply): User | null {
    const user = currentUser(request);
    if (!user) reply.code(401).send({ code: "unauthorized" });
    return user;
  }

  // [Implementation 6] Session and cookie issuance
  app.post("/auth/login", async (request, reply) => {
    const parsed = LoginSchema.safeParse(request.body);
    if (!parsed.success) return reply.code(400).send({ code: "invalid_request" });

    const user = store.findUserByHandle(parsed.data.handle);
    if (!user) return reply.code(401).send({ code: "unauthorized" });

    const session = store.createSession(user.id);
    reply.setCookie(SESSION_COOKIE, session.token, {
      path: "/",
      httpOnly: true,
      secure: production,
      sameSite: "lax",
      maxAge: session.maxAgeSeconds
    });
    return { user };
  });

  // [Implementation 7] Server and browser logout cleanup
  app.post("/auth/logout", async (request, reply) => {
    const token = request.cookies[SESSION_COOKIE];
    if (token) store.revokeSession(token);
    reply.clearCookie(SESSION_COOKIE, { path: "/" });
    return { ok: true };
  });

  app.get("/me", async (request, reply) => {
    const user = requireUser(request, reply);
    return user ? { user } : reply;
  });

  // [Implementation 8] Profile owner or admin check
  app.patch("/profiles/:id", async (request, reply) => {
    const actor = requireUser(request, reply);
    if (!actor) return reply;

    const { id } = request.params as { id: string };
    if (actor.id !== id && actor.role !== "admin") {
      return reply.code(403).send({ code: "forbidden" });
    }

    const parsed = ProfileSchema.safeParse(request.body);
    if (!parsed.success) return reply.code(400).send({ code: "invalid_request" });

    const user = store.updateDisplayName(id, parsed.data.displayName);
    return user
      ? { user }
      : reply.code(404).send({ code: "not_found" });
  });

  // [Implementation 9] Admin-only user listing
  app.get("/admin/users", async (request, reply) => {
    const actor = requireUser(request, reply);
    if (!actor) return reply;
    if (actor.role !== "admin") return reply.code(403).send({ code: "forbidden" });
    return { users: store.listUsers() };
  });

  return app;
}
