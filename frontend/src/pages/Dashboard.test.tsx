import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { API_URL, server } from "../test/server";
import { renderWithProviders, screen, waitFor } from "../test/test-utils";
import { Dashboard } from "./Dashboard";

describe("Dashboard", () => {
  it("renders the stat tiles from the API", async () => {
    renderWithProviders(<Dashboard />);

    await waitFor(() => expect(screen.getByText("Дашборд")).toBeInTheDocument());
    expect(screen.getByText("2")).toBeInTheDocument(); // due_today
    expect(screen.getByText("5")).toBeInTheDocument(); // total_words
    expect(screen.getByText("1")).toBeInTheDocument(); // mastered
    expect(screen.getByText("3")).toBeInTheDocument(); // streak_days
  });

  it("shows a review link with the due count when there are due cards", async () => {
    renderWithProviders(<Dashboard />);

    const link = await screen.findByText("Начать повторение (2)");
    expect(link.closest("a")).toHaveAttribute("href", "/review");
  });

  it("shows an empty-state message instead of a review link when nothing is due", async () => {
    server.use(
      http.get(`${API_URL}/stats/summary`, () =>
        HttpResponse.json({ total_words: 5, due_today: 0, streak_days: 0, mastered: 0, by_topic: [] })
      )
    );

    renderWithProviders(<Dashboard />);

    await waitFor(() =>
      expect(screen.getByText(/На сегодня карточек нет/)).toBeInTheDocument()
    );
    expect(screen.queryByText(/Начать повторение/)).not.toBeInTheDocument();
  });

  it("renders topic breakdown when present", async () => {
    renderWithProviders(<Dashboard />);

    await waitFor(() => expect(screen.getByText("По темам")).toBeInTheDocument());
    expect(screen.getByText("Еда · 2")).toBeInTheDocument();
  });

  it("hides the topics section when by_topic is empty", async () => {
    server.use(
      http.get(`${API_URL}/stats/summary`, () =>
        HttpResponse.json({ total_words: 0, due_today: 0, streak_days: 0, mastered: 0, by_topic: [] })
      )
    );

    renderWithProviders(<Dashboard />);

    await waitFor(() => expect(screen.getByText("Дашборд")).toBeInTheDocument());
    expect(screen.queryByText("По темам")).not.toBeInTheDocument();
  });
});
