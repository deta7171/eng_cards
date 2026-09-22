import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { API_URL, fixtureUserWord, fixtureWord, server } from "../test/server";
import { renderWithProviders, screen, userEvent, waitFor, within } from "../test/test-utils";
import { Words } from "./Words";

function emptyDeck() {
  server.use(
    http.get(`${API_URL}/user-words`, () => HttpResponse.json({ items: [], total: 0, page: 1 })),
    http.get(`${API_URL}/suggestions`, () => HttpResponse.json({ items: [] }))
  );
}

describe("Words - deck rendering", () => {
  it("renders the deck with count, translation and transcription", async () => {
    renderWithProviders(<Words />);

    await waitFor(() => expect(screen.getByText("Моя колода (1)")).toBeInTheDocument());
    expect(screen.getByText("apple")).toBeInTheDocument();
    expect(screen.getByText("яблоко")).toBeInTheDocument();
    expect(screen.getByText("/ˈæp.əl/")).toBeInTheDocument();
  });

  it("shows an empty state when the deck has no words", async () => {
    emptyDeck();
    renderWithProviders(<Words />);

    await waitFor(() => expect(screen.getByText("Моя колода (0)")).toBeInTheDocument());
    expect(screen.getByText(/Пока пусто/)).toBeInTheDocument();
  });

  it("renders suggestions and hides the section when there are none", async () => {
    renderWithProviders(<Words />);
    await waitFor(() => expect(screen.getByText(/\+ banana/)).toBeInTheDocument());
  });

  it("hides the suggestions section when empty", async () => {
    server.use(http.get(`${API_URL}/suggestions`, () => HttpResponse.json({ items: [] })));
    renderWithProviders(<Words />);

    await waitFor(() => expect(screen.getByText("Моя колода (1)")).toBeInTheDocument());
    expect(screen.queryByText("Предложенные слова")).not.toBeInTheDocument();
  });
});

describe("Words - adding a word", () => {
  it("submits the trimmed input, clears it, and shows the new word after refetch", async () => {
    const deck = [fixtureUserWord()];
    server.use(
      http.get(`${API_URL}/user-words`, () => HttpResponse.json({ items: deck, total: deck.length, page: 1 })),
      http.post(`${API_URL}/words`, async ({ request }) => {
        const { text } = (await request.json()) as { text: string };
        expect(text).toBe("Banana"); // frontend must trim before sending
        const uw = fixtureUserWord({
          user_word_id: "uw-new",
          // backend normalizes to lowercase - mirror that so this test
          // actually verifies the frontend trims before sending, not just
          // that whatever text comes back gets rendered
          word: fixtureWord({ id: "word-new", text: text.toLowerCase(), translation: "новое" }),
        });
        deck.push(uw);
        return HttpResponse.json(uw, { status: 201 });
      })
    );

    renderWithProviders(<Words />);
    await waitFor(() => expect(screen.getByText("Моя колода (1)")).toBeInTheDocument());

    const input = screen.getByPlaceholderText(/Введи английское слово/) as HTMLInputElement;
    await userEvent.type(input, "  Banana  ");
    await userEvent.click(screen.getByRole("button", { name: "Добавить" }));

    await waitFor(() => expect(screen.getByText("Моя колода (2)")).toBeInTheDocument());
    expect(screen.getByText("banana")).toBeInTheDocument();
    expect(input.value).toBe("");
  });

  it("does not submit when the input is empty or whitespace-only", async () => {
    let called = false;
    server.use(
      http.post(`${API_URL}/words`, () => {
        called = true;
        return HttpResponse.json({}, { status: 201 });
      })
    );

    renderWithProviders(<Words />);
    await waitFor(() => expect(screen.getByText("Моя колода (1)")).toBeInTheDocument());

    const input = screen.getByPlaceholderText(/Введи английское слово/);
    await userEvent.type(input, "   ");
    await userEvent.click(screen.getByRole("button", { name: "Добавить" }));

    expect(called).toBe(false);
  });

  it("shows the error message and keeps the input when the API call fails", async () => {
    server.use(http.post(`${API_URL}/words`, () => new HttpResponse("already in your deck", { status: 409 })));

    renderWithProviders(<Words />);
    await waitFor(() => expect(screen.getByText("Моя колода (1)")).toBeInTheDocument());

    const input = screen.getByPlaceholderText(/Введи английское слово/) as HTMLInputElement;
    await userEvent.type(input, "apple");
    await userEvent.click(screen.getByRole("button", { name: "Добавить" }));

    expect(await screen.findByText("already in your deck")).toBeInTheDocument();
    expect(input.value).toBe("apple");
  });

  it("shows a generic error message for a network failure (not an ApiError)", async () => {
    server.use(http.post(`${API_URL}/words`, () => HttpResponse.error()));

    renderWithProviders(<Words />);
    await waitFor(() => expect(screen.getByText("Моя колода (1)")).toBeInTheDocument());

    await userEvent.type(screen.getByPlaceholderText(/Введи английское слово/), "apple");
    await userEvent.click(screen.getByRole("button", { name: "Добавить" }));

    expect(await screen.findByText("Не удалось добавить слово")).toBeInTheDocument();
  });

  it("disables the submit button and shows progress text while adding", async () => {
    server.use(
      http.post(`${API_URL}/words`, async () => {
        await new Promise((r) => setTimeout(r, 30));
        return HttpResponse.json(fixtureUserWord(), { status: 201 });
      })
    );

    renderWithProviders(<Words />);
    await waitFor(() => expect(screen.getByText("Моя колода (1)")).toBeInTheDocument());

    await userEvent.type(screen.getByPlaceholderText(/Введи английское слово/), "apple");
    await userEvent.click(screen.getByRole("button", { name: "Добавить" }));

    expect(await screen.findByRole("button", { name: "Добавляем…" })).toBeDisabled();
  });
});

describe("Words - suggestions", () => {
  it("adding a suggestion removes it from suggestions and adds it to the deck", async () => {
    const deck = [fixtureUserWord()];
    const suggestionWord = fixtureWord({ id: "word-2", text: "banana", translation: "банан" });
    let suggestionsLeft = [suggestionWord];

    server.use(
      http.get(`${API_URL}/user-words`, () => HttpResponse.json({ items: deck, total: deck.length, page: 1 })),
      http.get(`${API_URL}/suggestions`, () => HttpResponse.json({ items: suggestionsLeft })),
      http.post(`${API_URL}/suggestions/:id/add`, ({ params }) => {
        expect(params.id).toBe("word-2");
        suggestionsLeft = [];
        deck.push(fixtureUserWord({ user_word_id: "uw-2", word: suggestionWord }));
        return HttpResponse.json({}, { status: 201 });
      })
    );

    renderWithProviders(<Words />);
    const suggestionButton = await screen.findByText(/\+ banana — банан/);
    await userEvent.click(suggestionButton);

    await waitFor(() => expect(screen.queryByText(/\+ banana/)).not.toBeInTheDocument());
    await waitFor(() => expect(screen.getByText("Моя колода (2)")).toBeInTheDocument());
  });
});

describe("Words - removing a word", () => {
  it("removes the word from the deck after clicking Убрать", async () => {
    const deck = [fixtureUserWord()];
    server.use(
      http.get(`${API_URL}/user-words`, () => HttpResponse.json({ items: deck, total: deck.length, page: 1 })),
      http.delete(`${API_URL}/user-words/:id`, ({ params }) => {
        expect(params.id).toBe("uw-1");
        deck.length = 0;
        return new HttpResponse(null, { status: 204 });
      })
    );

    renderWithProviders(<Words />);
    await waitFor(() => expect(screen.getByText("Моя колода (1)")).toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: "Убрать" }));

    await waitFor(() => expect(screen.getByText("Моя колода (0)")).toBeInTheDocument());
    expect(screen.getByText(/Пока пусто/)).toBeInTheDocument();
  });

  it("shows the topic tag next to a word that has one", async () => {
    server.use(
      http.get(`${API_URL}/user-words`, () =>
        HttpResponse.json({
          items: [fixtureUserWord({ word: fixtureWord({ topic: { slug: "food", name_ru: "Еда" } }) })],
          total: 1,
          page: 1,
        })
      )
    );

    renderWithProviders(<Words />);
    const card = (await screen.findByText("apple")).closest(".card") as HTMLElement;
    expect(within(card).getByText("Еда")).toBeInTheDocument();
  });
});
