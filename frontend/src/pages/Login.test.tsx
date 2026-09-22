import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { renderWithProviders, screen, waitFor } from "../test/test-utils";
import { API_URL, googleLoginUrl, setToken } from "../api/client";
import { Login } from "./Login";

function renderLogin() {
  return renderWithProviders(
    <Routes>
      <Route path="/" element={<Login />} />
      <Route path="/dashboard" element={<div>Dashboard content</div>} />
    </Routes>,
    { route: "/" }
  );
}

describe("Login", () => {
  it("shows a Google login link pointing at the backend, when logged out", async () => {
    renderLogin();

    await waitFor(() => expect(screen.getByText("Войти через Google")).toBeInTheDocument());
    const link = screen.getByText("Войти через Google") as HTMLAnchorElement;
    expect(link.href).toBe(`${API_URL}/auth/google/login`);
    expect(link.href).toBe(googleLoginUrl());
  });

  it("redirects to /dashboard when already authenticated", async () => {
    setToken("valid-token");
    renderLogin();

    await waitFor(() => expect(screen.getByText("Dashboard content")).toBeInTheDocument());
    expect(screen.queryByText("Войти через Google")).not.toBeInTheDocument();
  });
});
