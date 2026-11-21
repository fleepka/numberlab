import { useEffect, useState } from "react";
import { api } from "../api";
import type { RatingData } from "../types";

function nameOf(item: { username: string | null; first_name: string | null }): string {
  if (item.username) return `@${item.username}`;
  return item.first_name || "Игрок";
}

export function RatingView({
  selfId,
  notify,
}: {
  selfId: number;
  notify: (message: string, kind?: "ok" | "err") => void;
}) {
  const [data, setData] = useState<RatingData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .rating()
      .then(setData)
      .catch((error: Error) => notify(error.message, "err"))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) return <div className="view center muted">Считаем рейтинг…</div>;
  if (!data) return <div className="view center muted">Рейтинг недоступен</div>;

  return (
    <section className="view">
      <div className="card rating-me">
        <div>
          <div className="muted small">Твоё место</div>
          <div className="rating-place">№ {data.me.rank}</div>
        </div>
        <div className="rating-me-right">
          <div className="price">{data.me.total.toLocaleString("ru-RU")} М</div>
          <div className="muted small">{data.me.plates} номеров</div>
        </div>
      </div>

      <div className="section-head">
        <h2>Топ игроков</h2>
        <span className="muted small">по стоимости гаража</span>
      </div>

      <div className="task-list">
        {data.items.map((item, index) => (
          <article
            className={item.user_id === selfId ? "card rating-row rating-self" : "card rating-row"}
            key={item.user_id}
          >
            <span className={index < 3 ? "rating-rank rating-top" : "rating-rank"}>{index + 1}</span>
            <div className="rating-name">
              <div>{nameOf(item)}</div>
              <div className="muted small">{item.plates} номеров</div>
            </div>
            <span className="price">{item.total.toLocaleString("ru-RU")} М</span>
          </article>
        ))}
        {!data.items.length && <div className="card muted small">Пока никого — крути первый номер</div>}
      </div>
    </section>
  );
}
