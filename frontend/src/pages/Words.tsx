import { useState } from "react";
import type { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";
import type { UserWord, Word } from "../api/types";

interface UserWordListResponse {
  items: UserWord[];
  total: number;
  page: number;
}

export function Words() {
  const [newWord, setNewWord] = useState("");
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery<UserWordListResponse>({
    queryKey: ["user-words"],
    queryFn: () => api.get<UserWordListResponse>("/user-words?page=1"),
  });

  const { data: suggestions } = useQuery<{ items: Word[] }>({
    queryKey: ["suggestions"],
    queryFn: () => api.get<{ items: Word[] }>("/suggestions?count=6"),
  });

  const addWord = useMutation({
    mutationFn: (text: string) => api.post<UserWord>("/words", { text }),
    onSuccess: () => {
      setNewWord("");
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["user-words"] });
      queryClient.invalidateQueries({ queryKey: ["stats"] });
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "Не удалось добавить слово");
    },
  });

  const addSuggestion = useMutation({
    mutationFn: (wordId: string) => api.post<UserWord>(`/suggestions/${wordId}/add`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user-words"] });
      queryClient.invalidateQueries({ queryKey: ["suggestions"] });
      queryClient.invalidateQueries({ queryKey: ["stats"] });
    },
  });

  const removeWord = useMutation({
    mutationFn: (userWordId: string) => api.delete(`/user-words/${userWordId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user-words"] });
      queryClient.invalidateQueries({ queryKey: ["stats"] });
    },
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (newWord.trim()) addWord.mutate(newWord.trim());
  }

  return (
    <div>
      <h1>Слова</h1>

      <form onSubmit={handleSubmit} className="card" style={{ display: "flex", gap: 12, marginBottom: 24 }}>
        <input
          type="text"
          placeholder="Введи английское слово, например apple"
          value={newWord}
          onChange={(e) => setNewWord(e.target.value)}
        />
        <button className="btn" type="submit" disabled={addWord.isPending}>
          {addWord.isPending ? "Добавляем…" : "Добавить"}
        </button>
      </form>
      {error && <p style={{ color: "var(--color-danger)" }}>{error}</p>}

      {suggestions && suggestions.items.length > 0 && (
        <div style={{ marginBottom: 32 }}>
          <h2>Предложенные слова</h2>
          <div className="btn-row">
            {suggestions.items.map((w) => (
              <button
                key={w.id}
                className="btn-secondary btn"
                onClick={() => addSuggestion.mutate(w.id)}
                disabled={addSuggestion.isPending}
              >
                + {w.text} — {w.translation}
              </button>
            ))}
          </div>
        </div>
      )}

      <h2>Моя колода {data ? `(${data.total})` : ""}</h2>
      {isLoading && <p className="muted">Загрузка…</p>}
      {data && data.items.length === 0 && <p className="muted">Пока пусто — добавь первое слово выше.</p>}
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {data?.items.map((uw) => (
          <div
            key={uw.user_word_id}
            className="card"
            style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: 16 }}
          >
            <div>
              <strong>{uw.word.text}</strong> <span className="muted">{uw.word.transcription}</span>
              <div className="muted">{uw.word.translation}</div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              {uw.word.topic && <span className="muted">{uw.word.topic.name_ru}</span>}
              <button
                className="btn-secondary btn"
                onClick={() => removeWord.mutate(uw.user_word_id)}
                disabled={removeWord.isPending}
              >
                Убрать
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
