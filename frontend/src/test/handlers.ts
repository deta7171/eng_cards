import { http, HttpResponse } from "msw";

export const API_URL = "http://localhost:8000/api";

export const fixtureUser = {
  id: "user-1",
  email: "alice@example.com",
  name: "Alice",
  avatar_url: null,
};

export const fixtureWord = (overrides: Partial<Record<string, unknown>> = {}) => ({
  id: "word-1",
  text: "apple",
  translation: "яблоко",
  transcription: "/ˈæp.əl/",
  part_of_speech: "noun",
  examples: ["I ate an apple."],
  cefr_level: "A1",
  topic: null,
  ...overrides,
});

export const fixtureUserWord = (overrides: Partial<Record<string, unknown>> = {}) => ({
  user_word_id: "uw-1",
  word: fixtureWord(),
  fsrs_state: { state: "new", due_date: new Date().toISOString(), reps: 0, lapses: 0 },
  ...overrides,
});

export const fixtureStatsSummary = {
  total_words: 5,
  due_today: 2,
  streak_days: 3,
  mastered: 1,
  by_topic: [{ slug: "food", name_ru: "Еда", word_count: 2 }],
};

export const handlers = [
  http.get(`${API_URL}/auth/me`, ({ request }) => {
    const auth = request.headers.get("Authorization");
    if (!auth) return new HttpResponse("Not authenticated", { status: 401 });
    return HttpResponse.json(fixtureUser);
  }),

  http.get(`${API_URL}/stats/summary`, () => HttpResponse.json(fixtureStatsSummary)),

  http.get(`${API_URL}/user-words`, () =>
    HttpResponse.json({ items: [fixtureUserWord()], total: 1, page: 1 })
  ),

  http.post(`${API_URL}/words`, async ({ request }) => {
    const body = (await request.json()) as { text: string };
    return HttpResponse.json(
      fixtureUserWord({ word: fixtureWord({ text: body.text.trim().toLowerCase() }) }),
      { status: 201 }
    );
  }),

  http.delete(`${API_URL}/user-words/:id`, () => new HttpResponse(null, { status: 204 })),

  http.get(`${API_URL}/suggestions`, () => HttpResponse.json({ items: [fixtureWord({ id: "word-2", text: "banana", translation: "банан" })] })),

  http.post(`${API_URL}/suggestions/:id/add`, () => HttpResponse.json(fixtureUserWord(), { status: 201 })),

  http.get(`${API_URL}/review/queue`, () => HttpResponse.json({ items: [fixtureUserWord()] })),

  http.post(`${API_URL}/review/:id`, () =>
    HttpResponse.json({ fsrs_state: { state: "learning", due_date: new Date().toISOString(), reps: 1, lapses: 0 } })
  ),
];
