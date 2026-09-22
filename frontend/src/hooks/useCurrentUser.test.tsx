import { renderHook, waitFor } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { API_URL, server } from "../test/server";
import { makeQueryClient } from "../test/test-utils";
import { setToken } from "../api/client";
import { useCurrentUser } from "./useCurrentUser";

function wrapper({ children }: { children: React.ReactNode }) {
  const queryClient = makeQueryClient();
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

describe("useCurrentUser", () => {
  it("returns the user on success", async () => {
    setToken("valid-token");
    const { result } = renderHook(() => useCurrentUser(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.email).toBe("alice@example.com");
  });

  it("returns null (not an error) on 401", async () => {
    server.use(http.get(`${API_URL}/auth/me`, () => new HttpResponse("nope", { status: 401 })));

    const { result } = renderHook(() => useCurrentUser(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBeNull();
  });

  it("surfaces non-401 errors", async () => {
    server.use(http.get(`${API_URL}/auth/me`, () => new HttpResponse("boom", { status: 500 })));

    const { result } = renderHook(() => useCurrentUser(), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
