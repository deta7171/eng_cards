# API contract (MVP)

Base URL: `/api`. Auth via httpOnly cookie holding a JWT, issued after Google OAuth.
All endpoints below except `/auth/google/*` require an authenticated session.

## Auth

### `GET /auth/google/login`
Redirects to Google's OAuth consent screen.

### `GET /auth/google/callback`
Handles the OAuth redirect: exchanges code, finds-or-creates `users` row by
`google_id`, issues JWT as httpOnly cookie, redirects to frontend `/dashboard`.

### `GET /auth/me`
```json
{ "id": "uuid", "email": "...", "name": "...", "avatar_url": "..." }
```

### `POST /auth/logout`
Clears the session cookie.

---

## User words (my deck)

### `GET /user-words?page=1`
Paginated list of the current user's own deck, joined with word info and FSRS state.
Response shape: `{ "items": [ UserWordOut ], "total": 42, "page": 1 }` — same `UserWordOut`
shape as `POST /words` returns per item.

### `DELETE /user-words/{user_word_id}`
Removes the word from the current user's deck only (the global `words` row stays).

---

## Words (global dictionary / browsing)

### `GET /words?topic=food&level=A2&search=apple&page=1`
Paginated list from the shared dictionary. Used for search/browse UI.
```json
{ "items": [ { "id", "text", "translation", "transcription", "cefr_level", "topic": {"slug","name_ru"} } ], "total": 123, "page": 1 }
```

### `POST /words`
Add a new word to the shared dictionary (if missing) and to the current
user's deck in one step.
```json
// request
{ "text": "apple" }
// response — 201, may take ~1-2s: translation + dictionary lookups are synchronous on first-ever add, cached for everyone after
{
  "user_word_id": "uuid",
  "word": { "id", "text": "apple", "translation": "яблоко", "transcription": "/ˈæpəl/",
            "part_of_speech": "noun", "examples": ["I ate an apple."], "cefr_level": null, "topic": null },
  "fsrs_state": { "state": "new", "due_date": "2026-09-21T00:00:00Z" }
}
```

---

## Suggestions

### `GET /suggestions?topic=food&level=A2&count=10`
Returns up to `count` words from the seed dictionary matching the filters,
excluding words already in the user's deck.
```json
{ "items": [ { "id", "text", "translation", "cefr_level", "topic" } ] }
```

### `POST /suggestions/{word_id}/add`
Adds an existing dictionary word to the current user's deck (shortcut —
skips the translate/lookup step since the word already exists).
Response shape same as `POST /words`.

---

## Topics

### `GET /topics`
```json
{ "items": [ { "slug": "food", "name_ru": "Еда", "word_count": 84 } ] }
```

---

## Review

### `GET /review/queue?limit=20`
Cards due now for the current user, ordered by `due_date` ascending.
```json
{
  "items": [
    { "user_word_id", "word": { "text", "translation", "transcription", "examples" },
      "fsrs_state": { "state", "due_date", "reps" } }
  ]
}
```

### `POST /review/{user_word_id}`
Submits a review result; recalculates FSRS state server-side and logs it.
```json
// request
{ "activity_type": "flip", "rating": 3 }  // rating: 1 Again, 2 Hard, 3 Good, 4 Easy
// for multiple_choice / recall, frontend derives rating from correctness:
// correct -> 3 (Good), incorrect -> 1 (Again)

// response
{ "fsrs_state": { "state": "review", "due_date": "2026-09-24T00:00:00Z", "reps": 4, "lapses": 0 } }
```

---

## Stats

### `GET /stats/summary`
```json
{ "total_words": 240, "due_today": 12, "streak_days": 5, "mastered": 60,
  "by_topic": [ { "slug": "food", "name_ru": "Еда", "count": 30 } ] }
```

### `GET /stats/history?days=30`
```json
{ "items": [ { "date": "2026-09-20", "reviews": 24, "correct": 20 } ] }
```
