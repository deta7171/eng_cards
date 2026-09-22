import { beforeEach, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { API_URL, server } from "../test/server";
import { api, ApiError, clearToken, getToken, googleLoginUrl, setToken } from "./client";

describe("token storage", () => {
  beforeEach(() => clearToken());

  it("returns null when nothing is stored", () => {
    expect(getToken()).toBeNull();
  });

  it("round-trips a token", () => {
    setToken("abc123");
    expect(getToken()).toBe("abc123");
  });

  it("clears the token", () => {
    setToken("abc123");
    clearToken();
    expect(getToken()).toBeNull();
  });

  it("degrades to a no-op instead of throwing when localStorage is unavailable (e.g. private browsing)", () => {
    const originals = {
      getItem: Storage.prototype.getItem,
      setItem: Storage.prototype.setItem,
      removeItem: Storage.prototype.removeItem,
    };
    const throwing = () => {
      throw new Error("storage disabled");
    };
    Storage.prototype.getItem = throwing;
    Storage.prototype.setItem = throwing;
    Storage.prototype.removeItem = throwing;

    try {
      expect(getToken()).toBeNull();
      expect(() => setToken("x")).not.toThrow();
      expect(() => clearToken()).not.toThrow();
    } finally {
      Object.assign(Storage.prototype, originals);
    }
  });
});

describe("api client", () => {
  beforeEach(() => clearToken());

  it("does not send an Authorization header when no token is stored", async () => {
    let receivedAuth: string | null = "unset";
    server.use(
      http.get(`${API_URL}/probe`, ({ request }) => {
        receivedAuth = request.headers.get("Authorization");
        return HttpResponse.json({ ok: true });
      })
    );

    await api.get("/probe");
    expect(receivedAuth).toBeNull();
  });

  it("sends the stored token as a Bearer Authorization header", async () => {
    setToken("my-token");
    let receivedAuth: string | null = null;
    server.use(
      http.get(`${API_URL}/probe`, ({ request }) => {
        receivedAuth = request.headers.get("Authorization");
        return HttpResponse.json({ ok: true });
      })
    );

    await api.get("/probe");
    expect(receivedAuth).toBe("Bearer my-token");
  });

  it("serializes the POST body as JSON", async () => {
    let receivedBody: unknown = null;
    server.use(
      http.post(`${API_URL}/probe`, async ({ request }) => {
        receivedBody = await request.json();
        return HttpResponse.json({ ok: true }, { status: 201 });
      })
    );

    await api.post("/probe", { text: "apple" });
    expect(receivedBody).toEqual({ text: "apple" });
  });

  it("returns undefined for a 204 response", async () => {
    server.use(http.delete(`${API_URL}/probe`, () => new HttpResponse(null, { status: 204 })));
    const result = await api.delete("/probe");
    expect(result).toBeUndefined();
  });

  it("throws ApiError with the status code on a non-2xx response", async () => {
    server.use(http.get(`${API_URL}/probe`, () => new HttpResponse("boom", { status: 502 })));

    await expect(api.get("/probe")).rejects.toMatchObject({ status: 502 });
    await expect(api.get("/probe")).rejects.toBeInstanceOf(ApiError);
  });

  it("googleLoginUrl points at the backend login endpoint", () => {
    expect(googleLoginUrl()).toBe(`${API_URL}/auth/google/login`);
  });
});
