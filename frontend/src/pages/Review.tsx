import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { ActivityType, UserWord } from "../api/types";
import { RATING } from "../api/types";

const ACTIVITIES: ActivityType[] = ["flip", "multiple_choice", "recall"];

function pickActivity(seed: number): ActivityType {
  return ACTIVITIES[seed % ACTIVITIES.length];
}

export function Review() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery<{ items: UserWord[] }>({
    queryKey: ["review", "queue"],
    queryFn: () => api.get<{ items: UserWord[] }>("/review/queue?limit=20"),
  });

  const [index, setIndex] = useState(0);
  const submit = useMutation({
    mutationFn: (vars: { userWordId: string; activityType: ActivityType; rating: number }) =>
      api.post(`/review/${vars.userWordId}`, { activity_type: vars.activityType, rating: vars.rating }),
  });

  const items = data?.items ?? [];
  const current = items[index];
  const distractors = useMemo(
    () => items.filter((_, i) => i !== index).map((uw) => uw.word.translation),
    [items, index]
  );

  function next() {
    if (index + 1 >= items.length) {
      queryClient.invalidateQueries({ queryKey: ["stats"] });
      queryClient.invalidateQueries({ queryKey: ["review", "queue"] });
      setIndex((i) => i + 1); // moves past the end -> "done" screen
    } else {
      setIndex((i) => i + 1);
    }
  }

  function handleRate(rating: number) {
    if (!current) return;
    submit.mutate({ userWordId: current.user_word_id, activityType: pickActivity(index), rating });
    next();
  }

  if (isLoading) return <p className="muted">Загрузка…</p>;

  if (!items.length) {
    return (
      <div>
        <h1>Повторение</h1>
        <p className="muted">На сегодня карточек нет. Загляни в «Слова», чтобы добавить новые.</p>
        <Link className="btn" to="/words">
          К словам
        </Link>
      </div>
    );
  }

  if (index >= items.length) {
    return (
      <div>
        <h1>Готово 🎉</h1>
        <p className="muted">Все карточки на сегодня повторены.</p>
        <Link className="btn" to="/dashboard">
          На дашборд
        </Link>
      </div>
    );
  }

  const activity = pickActivity(index);

  return (
    <div>
      <p className="muted">
        Карточка {index + 1} из {items.length}
      </p>
      {activity === "flip" && <FlipCard word={current.word} onRate={handleRate} />}
      {activity === "multiple_choice" && (
        <MultipleChoiceCard word={current.word} distractors={distractors} onAnswer={handleRate} />
      )}
      {activity === "recall" && <RecallCard word={current.word} onAnswer={handleRate} />}
    </div>
  );
}

function FlipCard({ word, onRate }: { word: UserWord["word"]; onRate: (rating: number) => void }) {
  const [flipped, setFlipped] = useState(false);

  return (
    <div className="card" style={{ textAlign: "center", padding: 48 }}>
      <div style={{ fontSize: 32, fontWeight: 600 }}>{flipped ? word.translation : word.text}</div>
      {!flipped && word.transcription && <div className="muted">{word.transcription}</div>}

      {!flipped ? (
        <button className="btn" style={{ marginTop: 24 }} onClick={() => setFlipped(true)}>
          Показать перевод
        </button>
      ) : (
        <div className="btn-row" style={{ marginTop: 24, justifyContent: "center" }}>
          <button className="btn-secondary btn" onClick={() => onRate(RATING.AGAIN)}>
            Забыл
          </button>
          <button className="btn-secondary btn" onClick={() => onRate(RATING.HARD)}>
            Сложно
          </button>
          <button className="btn" onClick={() => onRate(RATING.GOOD)}>
            Хорошо
          </button>
          <button className="btn" onClick={() => onRate(RATING.EASY)}>
            Легко
          </button>
        </div>
      )}
    </div>
  );
}

function MultipleChoiceCard({
  word,
  distractors,
  onAnswer,
}: {
  word: UserWord["word"];
  distractors: string[];
  onAnswer: (rating: number) => void;
}) {
  const [selected, setSelected] = useState<string | null>(null);

  const options = useMemo(() => {
    const wrong = [...distractors].sort(() => Math.random() - 0.5).slice(0, 3);
    return [...wrong, word.translation].sort(() => Math.random() - 0.5);
  }, [word, distractors]);

  function choose(option: string) {
    if (selected) return;
    setSelected(option);
    const rating = option === word.translation ? RATING.GOOD : RATING.AGAIN;
    setTimeout(() => onAnswer(rating), 700);
  }

  return (
    <div className="card" style={{ textAlign: "center", padding: 48 }}>
      <div style={{ fontSize: 32, fontWeight: 600 }}>{word.text}</div>
      <div style={{ display: "grid", gap: 10, marginTop: 24 }}>
        {options.map((opt) => {
          const isCorrect = opt === word.translation;
          const showState = selected && (isCorrect || opt === selected);
          return (
            <button
              key={opt}
              className={showState ? "btn" : "btn-secondary btn"}
              style={showState ? { background: isCorrect ? "var(--color-success)" : "var(--color-danger)" } : undefined}
              onClick={() => choose(opt)}
              disabled={!!selected}
            >
              {opt}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function RecallCard({ word, onAnswer }: { word: UserWord["word"]; onAnswer: (rating: number) => void }) {
  const [value, setValue] = useState("");
  const [result, setResult] = useState<"correct" | "wrong" | null>(null);

  function submit() {
    if (result) return;
    const correct = value.trim().toLowerCase() === word.text.trim().toLowerCase();
    setResult(correct ? "correct" : "wrong");
    setTimeout(() => onAnswer(correct ? RATING.GOOD : RATING.AGAIN), 900);
  }

  return (
    <div className="card" style={{ textAlign: "center", padding: 48 }}>
      <div style={{ fontSize: 32, fontWeight: 600 }}>{word.translation}</div>
      <div style={{ marginTop: 24, display: "flex", gap: 10, justifyContent: "center" }}>
        <input
          type="text"
          placeholder="напиши слово по-английски"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          disabled={!!result}
          style={{ maxWidth: 260 }}
        />
        <button className="btn" onClick={submit} disabled={!!result}>
          Проверить
        </button>
      </div>
      {result && (
        <p style={{ marginTop: 16, color: result === "correct" ? "var(--color-success)" : "var(--color-danger)" }}>
          {result === "correct" ? "Верно!" : `Правильный ответ: ${word.text}`}
        </p>
      )}
    </div>
  );
}
