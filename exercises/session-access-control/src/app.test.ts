import { describe, expect, it } from "vitest";

import { buildApp } from "./app";
import { InMemorySecurityStore } from "./store";

const trustedOrigin = "http://localhost:3000";

function cookieOf(response: { headers: Record<string, string | string[] | number | undefined> }): string {
  const value = response.headers["set-cookie"];
  return String(Array.isArray(value) ? value[0] : value).split(";")[0] ?? "";
}

describe("세션과 권한", () => {
  it("인증 실패, 역할 부족과 소유권 부족을 구분합니다", async () => {
    const app = buildApp({ store: new InMemorySecurityStore() });
    await app.ready();
    try {
      expect((await app.inject({ method: "GET", url: "/me" })).statusCode).toBe(401);

      const login = await app.inject({
        method: "POST",
        url: "/auth/login",
        payload: { handle: "alpha" }
      });
      const cookie = cookieOf(login);
      const setCookie = String(login.headers["set-cookie"]);
      expect(setCookie).toContain("HttpOnly");
      expect(setCookie).toContain("SameSite=Lax");
      expect(setCookie).toContain("Path=/");

      expect((await app.inject({
        method: "GET",
        url: "/admin/users",
        headers: { cookie }
      })).statusCode).toBe(403);

      expect((await app.inject({
        method: "PATCH",
        url: "/profiles/u-admin",
        headers: { cookie, origin: trustedOrigin },
        payload: { displayName: "변경 시도" }
      })).statusCode).toBe(403);
    } finally {
      await app.close();
    }
  });

  it("신뢰하지 않거나 없는 Origin은 상태 변경 전에 거부합니다", async () => {
    const app = buildApp({ store: new InMemorySecurityStore() });
    await app.ready();
    try {
      const login = await app.inject({ method: "POST", url: "/auth/login", payload: { handle: "alpha" } });
      const cookie = cookieOf(login);

      for (const origin of ["https://attacker.invalid", "https://evil-localhost:3000", undefined]) {
        const response = await app.inject({
          method: "PATCH",
          url: "/profiles/u-alpha",
          headers: origin ? { cookie, origin } : { cookie },
          payload: { displayName: "거부 대상" }
        });
        expect(response.statusCode).toBe(403);
        expect(response.json()).toEqual({ code: "origin_forbidden" });
      }

      const me = await app.inject({ method: "GET", url: "/me", headers: { cookie } });
      expect(me.json().user.displayName).toBe("알파");
    } finally {
      await app.close();
    }
  });

  it("신뢰하지 않는 Origin의 브라우저 로그인을 거부합니다", async () => {
    const app = buildApp({ store: new InMemorySecurityStore() });
    await app.ready();
    try {
      const response = await app.inject({
        method: "POST",
        url: "/auth/login",
        headers: { origin: "https://attacker.invalid" },
        payload: { handle: "alpha" }
      });
      expect(response.statusCode).toBe(403);
      expect(response.headers["set-cookie"]).toBeUndefined();
    } finally {
      await app.close();
    }
  });

  it("로그아웃하면 서버 세션도 폐기합니다", async () => {
    const app = buildApp({ store: new InMemorySecurityStore() });
    await app.ready();
    try {
      const login = await app.inject({ method: "POST", url: "/auth/login", payload: { handle: "alpha" } });
      const cookie = cookieOf(login);
      expect((await app.inject({
        method: "POST",
        url: "/auth/logout",
        headers: { cookie, origin: trustedOrigin }
      })).statusCode).toBe(200);
      expect((await app.inject({ method: "GET", url: "/me", headers: { cookie } })).statusCode).toBe(401);
    } finally {
      await app.close();
    }
  });

  it("애플리케이션 인스턴스끼리 세션을 공유하지 않습니다", async () => {
    const first = buildApp({ store: new InMemorySecurityStore() });
    const second = buildApp({ store: new InMemorySecurityStore() });
    await Promise.all([first.ready(), second.ready()]);
    try {
      const login = await first.inject({ method: "POST", url: "/auth/login", payload: { handle: "alpha" } });
      const cookie = cookieOf(login);
      expect((await first.inject({ method: "GET", url: "/me", headers: { cookie } })).statusCode).toBe(200);
      expect((await second.inject({ method: "GET", url: "/me", headers: { cookie } })).statusCode).toBe(401);
    } finally {
      await Promise.all([first.close(), second.close()]);
    }
  });

  it("브라우저 쿠키와 서버 세션에 같은 만료 시간을 사용합니다", async () => {
    let now = 0;
    const store = new InMemorySecurityStore(() => now, 1);
    const app = buildApp({ store });
    await app.ready();
    try {
      const login = await app.inject({ method: "POST", url: "/auth/login", payload: { handle: "alpha" } });
      const cookie = cookieOf(login);
      expect(String(login.headers["set-cookie"])).toContain("Max-Age=1");
      expect((await app.inject({ method: "GET", url: "/me", headers: { cookie } })).statusCode).toBe(200);

      now = 1_000;
      expect((await app.inject({ method: "GET", url: "/me", headers: { cookie } })).statusCode).toBe(401);
    } finally {
      await app.close();
    }
  });
});
