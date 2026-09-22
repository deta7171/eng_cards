import { http, HttpResponse, delay } from "msw";
import { describe, expect, it } from "vitest";
import { API_URL, fixtureUserWord, fixtureWord, server } from "../test/server";
import { renderWithProviders, screen, userEvent, waitFor } from "../test/test-utils";
import { Review } from "./Review";

// index 0 -> flip, index 1 -> multiple_choice, index 2 -> recall (pickActivity = seed % 3)
const QUEUE = [
  fixtureUserWord({
    user_word_id: "uw-0",
    word: fixtureWord({ id: "w-0", text: "apple", translation: "яблоко", transcription: "/ˈæp.əl/" }),
  }),
  fixtureUserWord({
    user_word_id: "uw-1",
    word: fixtureWord({ id: "w-1", text: "banana", translation: "банан", transcription: null }),
  }),
  fixtureUserWord({
    user_word_id: "uw-2",
    word: fixtureWord({ id: "w-2", text: "cherry", translation: "вишня", transcription: null }),
  }),
];

function mockQueue(items = QUEUE) {
  server.use(http.get(`${API_URL}/review/queue`, () => HttpResponse.json({ items })));
}

function mockSubmit(onSubmit?: (id: string, body: { activity_type: string; rating: number }) => void) {
  server.use(
    http.post(`${API_URL}/review/:id`, async ({ request, params }) => {
      const body = (await request.json()) as { activity_type: string; rating: number };
      onSubmit?.(params.id as string, body);
      return HttpResponse.json({ fsrs_state: { state: "review", due_date: new Date().toISOString(), reps: 1, lapses: 0 } });
    })
  );
}

describe("Review - queue states", () => {
  it("shows a loading state while the queue is being fetched", async () => {
    server.use(
      http.get(`${API_URL}/review/queue`, async () => {
        await delay(50);
        return HttpResponse.json({ items: [] });
      })
    );
    renderWithProviders(<Review />);
    expect(screen.getByText("Загрузка…")).toBeInTheDocument();
  });

  it("shows an empty-queue message with a link to /words when there is nothing due", async () => {
    mockQueue([]);
    renderWithProviders(<Review />);

    await waitFor(() => expect(screen.getByText(/На сегодня карточек нет/)).toBeInTheDocument());
    expect(screen.getByText("К словам").closest("a")).toHaveAttribute("href", "/words");
  });

  it("shows progress text for the current card", async () => {
    mockQueue();
    renderWithProviders(<Review />);
    await waitFor(() => expect(screen.getByText("Карточка 1 из 3")).toBeInTheDocument());
  });
});

describe("Review - flip activity (card 1)", () => {
  it("shows the word first, then the translation after flipping, then rating buttons", async () => {
    mockQueue();
    renderWithProviders(<Review />);

    await waitFor(() => expect(screen.getByText("apple")).toBeInTheDocument());
    expect(screen.getByText("/ˈæp.əl/")).toBeInTheDocument();
    expect(screen.queryByText("яблоко")).not.toBeInTheDocument();

    await userEvent.click(screen.getByText("Показать перевод"));

    expect(screen.getByText("яблоко")).toBeInTheDocument();
    expect(screen.queryByText("apple")).not.toBeInTheDocument();
    expect(screen.getByText("Хорошо")).toBeInTheDocument();
  });

  it("submits activity_type=flip with the chosen rating and advances to card 2", async () => {
    mockQueue();
    let submitted: { activity_type: string; rating: number } | null = null;
    let submittedId: string | null = null;
    mockSubmit((id, body) => {
      submittedId = id;
      submitted = body;
    });

    renderWithProviders(<Review />);
    await waitFor(() => expect(screen.getByText("apple")).toBeInTheDocument());
    await userEvent.click(screen.getByText("Показать перевод"));
    await userEvent.click(screen.getByText("Хорошо"));

    await waitFor(() => expect(screen.getByText("Карточка 2 из 3")).toBeInTheDocument());
    expect(submittedId).toBe("uw-0");
    expect(submitted).toEqual({ activity_type: "flip", rating: 3 });
  });

  it.each([
    ["Забыл", 1],
    ["Сложно", 2],
    ["Хорошо", 3],
    ["Легко", 4],
  ])("%s sends rating=%i", async (label, expectedRating) => {
    mockQueue();
    let ratings: number[] = [];
    mockSubmit((_id, body) => ratings.push(body.rating));

    renderWithProviders(<Review />);
    await waitFor(() => expect(screen.getByText("apple")).toBeInTheDocument());
    await userEvent.click(screen.getByText("Показать перевод"));
    await userEvent.click(screen.getByText(label));

    await waitFor(() => expect(ratings).toEqual([expectedRating]));
  });
});

describe("Review - multiple choice activity (card 2)", () => {
  async function getToCardTwo() {
    mockQueue();
    mockSubmit();
    renderWithProviders(<Review />);
    await waitFor(() => expect(screen.getByText("apple")).toBeInTheDocument());
    await userEvent.click(screen.getByText("Показать перевод"));
    await userEvent.click(screen.getByText("Хорошо"));
    await waitFor(() => expect(screen.getByText("Карточка 2 из 3")).toBeInTheDocument());
  }

  it("shows the English word and translation options including the correct one", async () => {
    await getToCardTwo();

    expect(screen.getByText("banana")).toBeInTheDocument();
    expect(screen.getByText("банан")).toBeInTheDocument();
  });

  it("choosing the correct translation submits rating=Good and advances", async () => {
    await getToCardTwo();

    let submitted: { activity_type: string; rating: number } | null = null;
    mockSubmit((_id, body) => (submitted = body));

    await userEvent.click(screen.getByText("банан"));

    await waitFor(() => expect(screen.getByText("Карточка 3 из 3")).toBeInTheDocument(), { timeout: 2000 });
    expect(submitted).toEqual({ activity_type: "multiple_choice", rating: 3 });
  });

  it("choosing a wrong translation submits rating=Again and advances", async () => {
    await getToCardTwo();

    let submitted: { activity_type: string; rating: number } | null = null;
    mockSubmit((_id, body) => (submitted = body));

    // any option that isn't the correct "банан" - "яблоко" (from card 1) is a guaranteed distractor
    await userEvent.click(screen.getByText("яблоко"));

    await waitFor(() => expect(screen.getByText("Карточка 3 из 3")).toBeInTheDocument(), { timeout: 2000 });
    expect(submitted).toEqual({ activity_type: "multiple_choice", rating: 1 });
  });

  it("disables all options once one is chosen", async () => {
    await getToCardTwo();

    await userEvent.click(screen.getByText("банан"));

    for (const button of screen.getAllByRole("button")) {
      expect(button).toBeDisabled();
    }
  });

});

describe("Review - recall activity (card 3)", () => {
  async function getToCardThree() {
    mockQueue();
    mockSubmit();
    renderWithProviders(<Review />);
    await waitFor(() => expect(screen.getByText("apple")).toBeInTheDocument());
    await userEvent.click(screen.getByText("Показать перевод"));
    await userEvent.click(screen.getByText("Хорошо"));
    await waitFor(() => expect(screen.getByText("Карточка 2 из 3")).toBeInTheDocument());
    await userEvent.click(screen.getByText("банан"));
    await waitFor(() => expect(screen.getByText("Карточка 3 из 3")).toBeInTheDocument(), { timeout: 2000 });
  }

  it("shows the translation as the prompt", async () => {
    await getToCardThree();
    expect(screen.getByText("вишня")).toBeInTheDocument();
  });

  it("correct (case-insensitive, trimmed) answer shows success and submits rating=Good", async () => {
    await getToCardThree();

    let submitted: { activity_type: string; rating: number } | null = null;
    mockSubmit((_id, body) => (submitted = body));

    await userEvent.type(screen.getByPlaceholderText(/напиши слово/), "  CHERRY  ");
    await userEvent.click(screen.getByText("Проверить"));

    expect(await screen.findByText("Верно!")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("Готово 🎉")).toBeInTheDocument(), { timeout: 2000 });
    expect(submitted).toEqual({ activity_type: "recall", rating: 3 });
  });

  it("wrong answer shows the correct word and submits rating=Again", async () => {
    await getToCardThree();

    let submitted: { activity_type: string; rating: number } | null = null;
    mockSubmit((_id, body) => (submitted = body));

    await userEvent.type(screen.getByPlaceholderText(/напиши слово/), "wrong");
    await userEvent.click(screen.getByText("Проверить"));

    expect(await screen.findByText("Правильный ответ: cherry")).toBeInTheDocument();
    await waitFor(() => expect(submitted).toEqual({ activity_type: "recall", rating: 1 }), { timeout: 2000 });
  });

  it("submits on Enter key as well as button click", async () => {
    await getToCardThree();
    mockSubmit();

    const input = screen.getByPlaceholderText(/напиши слово/);
    await userEvent.type(input, "cherry{Enter}");

    expect(await screen.findByText("Верно!")).toBeInTheDocument();
  });

  it("disables the input and button once an answer was submitted", async () => {
    await getToCardThree();
    mockSubmit();

    await userEvent.type(screen.getByPlaceholderText(/напиши слово/), "cherry");
    await userEvent.click(screen.getByText("Проверить"));

    expect(await screen.findByText("Верно!")).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/напиши слово/)).toBeDisabled();
    expect(screen.getByText("Проверить")).toBeDisabled();
  });
});

describe("Review - completion", () => {
  it("shows the done screen with a link to /dashboard after the last card", async () => {
    mockQueue([QUEUE[0]]); // single flip card
    mockSubmit();
    renderWithProviders(<Review />);

    await waitFor(() => expect(screen.getByText("apple")).toBeInTheDocument());
    await userEvent.click(screen.getByText("Показать перевод"));
    await userEvent.click(screen.getByText("Хорошо"));

    await waitFor(() => expect(screen.getByText("Готово 🎉")).toBeInTheDocument());
    expect(screen.getByText("На дашборд").closest("a")).toHaveAttribute("href", "/dashboard");
  });
});
