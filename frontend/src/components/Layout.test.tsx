import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { renderWithProviders, screen, userEvent } from "../test/test-utils";
import { getToken, setToken } from "../api/client";
import { Layout } from "./Layout";

function renderLayout() {
  return renderWithProviders(
    <Routes>
      <Route path="/" element={<div>Login page</div>} />
      <Route element={<Layout />}>
        <Route path="/dashboard" element={<div>Dashboard content</div>} />
      </Route>
    </Routes>,
    { route: "/dashboard" }
  );
}

describe("Layout", () => {
  it("renders navigation links and the outlet content", () => {
    renderLayout();
    expect(screen.getByText("Дашборд")).toBeInTheDocument();
    expect(screen.getByText("Слова")).toBeInTheDocument();
    expect(screen.getByText("Повторение")).toBeInTheDocument();
    expect(screen.getByText("Dashboard content")).toBeInTheDocument();
  });

  it("marks the nav link for the current route as active and leaves the others inactive", () => {
    renderLayout(); // rendered at /dashboard

    expect(screen.getByText("Дашборд")).toHaveClass("active");
    expect(screen.getByText("Слова")).not.toHaveClass("active");
    expect(screen.getByText("Повторение")).not.toHaveClass("active");
  });

  it("clears the token and navigates to / on logout", async () => {
    setToken("some-token");
    renderLayout();

    await userEvent.click(screen.getByText("Выйти"));

    expect(getToken()).toBeNull();
    expect(await screen.findByText("Login page")).toBeInTheDocument();
  });
});
