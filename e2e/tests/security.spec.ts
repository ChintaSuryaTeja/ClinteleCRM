import { expect, test } from "@playwright/test";

// Checks of the production setup itself (Nginx + API settings), not of features.

test("plain HTTP is redirected to HTTPS", async ({ request, baseURL }) => {
  const httpUrl = baseURL!.replace(/^https:/, "http:") + "/login";
  const response = await request.get(httpUrl, { maxRedirects: 0 });

  expect(response.status()).toBe(301);
  expect(response.headers()["location"]).toMatch(/^https:\/\/.+\/login$/);
});

test("security headers are sent and the framework isn't announced", async ({ request }) => {
  const headers = (await request.get("/login")).headers();

  expect(headers["strict-transport-security"]).toMatch(/^max-age=\d+$/);
  expect(headers["x-content-type-options"]).toBe("nosniff");
  expect(headers["x-frame-options"]).toBe("SAMEORIGIN");
  expect(headers["referrer-policy"]).toBe("strict-origin-when-cross-origin");
  expect(headers["x-powered-by"]).toBeUndefined();
  expect(headers["server"]).toBe("nginx"); // no version number
});

test("internal API pages are not reachable from outside", async ({ request }) => {
  for (const path of ["/api/docs", "/api/redoc", "/api/openapi.json", "/api/metrics"]) {
    expect((await request.get(path)).status(), path).toBe(404);
  }
  expect(await (await request.get("/api/health/db")).json()).toEqual({ status: "ok" });
});

test("the login cookie is Secure and HttpOnly", async ({ request }) => {
  const response = await request.post("/api/auth/signup", {
    data: {
      organization_name: "E2E Cookie",
      email: `cookie-${Date.now()}@e2e.example.com`,
      password: "e2e-password-123",
      currency: "USD",
    },
  });
  expect(response.status()).toBe(201);
  const cookie = response.headers()["set-cookie"];

  expect(cookie).toContain("HttpOnly");
  expect(cookie).toContain("Secure");
  expect(cookie).toContain("SameSite=lax");
});
