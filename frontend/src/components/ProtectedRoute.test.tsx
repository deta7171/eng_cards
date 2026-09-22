import { Route, Routes } from "react-router-dom";
import { http, HttpResponse, delay } from "msw";
import { describe, expect, it } from "vitest";
import { API_URL, server } from "../test/server";
import { renderWithProviders, screen, waitFor } from "../test/test-utils";
import { setToken } from "../api/client";
import { ProtectedRoute } from "./ProtectedRoute";

function renderProtected(route: string) {
  return renderWithProviders(
    <Routes>
      <Route path="/" element={<div>Login page</div>} />
      <Route element={<ProtectedRoute />}>
        <Route path="/dashboard" element={<div>Dashboard content</div>} />
      </Route>
    </Routes>,
    { route }
  );
}

describe("ProtectedRoute", () => {
  it("shows a loading state while the auth check is in flight", async () => {
    server.use(
      http.get(`${API_URL}/auth/me`, async () => {
        await delay(50);
        return HttpResponse.json({ id: "1", email: "a@a.com", name: null, avatar_url: null });
      })
    );
    setToken("token");

    renderProtected("/dashboard");
    expect(screen.getByText("Загрузка…")).toBeInTheDocument();
  });

  it("redirects to / when there is no logged-in user", async () => {
    renderProtected("/dashboard");

    await waitFor(() => expect(screen.getByText("Login page")).toBeInTheDocument());
    expect(screen.queryByText("Dashboard content")).not.toBeInTheDocument();
  });

  it("renders the protected content when authenticated", async () => {
    setToken("token");

    renderProtected("/dashboard");

    await waitFor(() => expect(screen.getByText("Dashboard content")).toBeInTheDocument());
  });
});
