import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { renderWithProviders, screen, waitFor } from "../test/test-utils";
import { getToken } from "../api/client";
import { AuthCallback } from "./AuthCallback";

function renderCallback(route: string) {
  return renderWithProviders(
    <Routes>
      <Route path="/" element={<div>Login page</div>} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      <Route path="/dashboard" element={<div>Dashboard content</div>} />
    </Routes>,
    { route }
  );
}

describe("AuthCallback", () => {
  it("stores the token from the query string and redirects to /dashboard", async () => {
    renderCallback("/auth/callback?token=abc123");

    await waitFor(() => expect(screen.getByText("Dashboard content")).toBeInTheDocument());
    expect(getToken()).toBe("abc123");
  });

  it("redirects to / without storing anything when there is no token", async () => {
    renderCallback("/auth/callback");

    await waitFor(() => expect(screen.getByText("Login page")).toBeInTheDocument());
    expect(getToken()).toBeNull();
  });
});
