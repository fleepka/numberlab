import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { money } from "../format";
import type { RatingData, RatingItem } from "../types";

type Period = "season" | "week";

function nameOf(item: RatingItem): string {
  if (item.username) return `@${item.username}`;
  return item.first_name || "Игрок";
}

function initial(item: RatingItem): string {
  return (item.first_name || item.username || "И").slice(0, 1).toUpperCase();
}

function PodiumCard({ item, place }: { item: RatingItem; place: number }) {
  return (
    <div className={place === 1 ? "podium-card podium-first" : "podium-card"}>
      <div className="podium-avatar">
        <span>{initial(item)}</span>
        <span className="podium-place">{place}</span>
      </div>
      <div className="podium-name">{nameOf(item)}</div>
      <div className="podium-total">{money(item.total)}</div>
      <div className="muted small">{item.plates} номеров</div>
    </div>
  );
}

export function RatingView({
  selfId,
  notify,
}: {
  selfId: number;
  notify: (message: string, kind?: "ok" | "err") => void;
}) {
  const [period, setPeriod] = useState<Period>("season");
  const [data, setData] = useState<RatingData | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(
    async (next: Period) => {
      setLoading(true);
      try {
        setData(await api.rating(next));
      } catch (error) {
        notify((error as Error).message, "err");
      } finally {
        setLoading(false);
      }
    },
    [notify],
  );

  useEffect(() => {
    void load(period);
  }, [load, period]);

  const items = data?.items ?? [];
  const top = items.slice(0, 3);
  const rest = items.slice(3);

  return (
    <section className="view">
      <div className="section-head">
        <h2>Рейтинг</h2>
      </div>

      <div className="segmented">
        <button
          className={period === "season" ? "segment segment-active" : "segment"}
          onClick={() => setPeriod("season")}
        >
          Сезон
        </button>
        <button
          className={period === "week" ? "segment segment-active" : "segment"}
          onClick={() => setPeriod("week")}
        >
          Неделя
        </button>
      </div>

      <div className="card muted small">
        {period === "season"
          ? "Сумма номеров в гараже сейчас: продал — место падает."
          : "Стоимость номеров, добытых за текущую неделю."}
      </div>

      {loading && <div className="muted small">Считаем…</div>}

      {!loading && top.length > 0 && (
        <div className="podium">
          {top[1] && <PodiumCard item={top[1]} place={2} />}
          {top[0] && <PodiumCard item={top[0]} place={1} />}
          {top[2] && <PodiumCard item={top[2]} place={3} />}
        </div>
      )}

      <div className="card rating-me">
        <div>
          <div className="muted small">Твоё место</div>
          <div className="rating-place">№ {data?.me.rank ?? 0}</div>
        </div>
        <div className="rating-me-right">
          <div className="price">{money(data?.me.total ?? 0)}</div>
          <div className="muted small">{data?.me.plates ?? 0} номеров</div>
        </div>
      </div>

      <div className="task-list">
        {rest.map((item, index) => (
          <article
            className={item.user_id === selfId ? "card rating-row rating-self" : "card rating-row"}
            key={item.user_id}
          >
            <span className="rating-rank">{index + 4}</span>
            <div className="rating-name">
              <div>{nameOf(item)}</div>
              <div className="muted small">{item.plates} номеров</div>
            </div>
            <span className="price">{money(item.total)}</span>
          </article>
        ))}
        {!loading && !items.length && (
          <div className="card muted small">Пока никого — крути первый номер</div>
        )}
      </div>
    </section>
  );
}
