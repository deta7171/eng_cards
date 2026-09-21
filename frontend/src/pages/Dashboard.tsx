import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";

interface StatsSummary {
  total_words: number;
  due_today: number;
  streak_days: number;
  mastered: number;
  by_topic: { slug: string; name_ru: string; word_count: number }[];
}

export function Dashboard() {
  const { data, isLoading } = useQuery<StatsSummary>({
    queryKey: ["stats", "summary"],
    queryFn: () => api.get<StatsSummary>("/stats/summary"),
  });

  if (isLoading || !data) return <p className="muted">Загрузка…</p>;

  return (
    <div>
      <h1>Дашборд</h1>

      <div className="stat-grid">
        <div className="stat-tile">
          <div className="value">{data.due_today}</div>
          <div className="label">на сегодня</div>
        </div>
        <div className="stat-tile">
          <div className="value">{data.total_words}</div>
          <div className="label">всего слов</div>
        </div>
        <div className="stat-tile">
          <div className="value">{data.mastered}</div>
          <div className="label">выучено</div>
        </div>
        <div className="stat-tile">
          <div className="value">{data.streak_days}</div>
          <div className="label">дней подряд</div>
        </div>
      </div>

      {data.due_today > 0 ? (
        <Link className="btn" to="/review">
          Начать повторение ({data.due_today})
        </Link>
      ) : (
        <p className="muted">На сегодня карточек нет — загляни в «Слова», чтобы добавить новые.</p>
      )}

      {data.by_topic.length > 0 && (
        <div style={{ marginTop: 40 }}>
          <h2>По темам</h2>
          <div className="btn-row">
            {data.by_topic.map((t) => (
              <span key={t.slug} className="card" style={{ padding: "8px 14px" }}>
                {t.name_ru} · {t.word_count}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
