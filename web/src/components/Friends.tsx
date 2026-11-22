import { useEffect, useState } from "react";
import { api, tg } from "../api";
import { money } from "../format";
import type { FriendsData, RatingData } from "../types";

function nameOf(item: { username: string | null; first_name: string | null }): string {
  if (item.username) return `@${item.username}`;
  return item.first_name || "Игрок";
}

export function FriendsView({
  selfId,
  notify,
}: {
  selfId: number;
  notify: (message: string, kind?: "ok" | "err") => void;
}) {
  const [friends, setFriends] = useState<FriendsData | null>(null);
  const [leaders, setLeaders] = useState<RatingData | null>(null);

  useEffect(() => {
    api
      .friends()
      .then(setFriends)
      .catch((error: Error) => notify(error.message, "err"));
    api
      .rating()
      .then(setLeaders)
      .catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!friends) return <div className="view center muted">Загружаем друзей…</div>;

  const next = friends.ladder.find((step) => !step.done);
  const top = (leaders?.items ?? []).slice(0, 5);

  function invite() {
    const url = friends?.link;
    if (!url) return;
    if (tg?.openTelegramLink) tg.openTelegramLink(url);
    else window.open(url, "_blank");
  }

  return (
    <section className="view">
      <div className="section-head">
        <h2>Пригласи друзей</h2>
        <span className="muted small">{friends.invites} пришло</span>
      </div>

      <div className="ladder">
        {friends.ladder.map((step) => {
          const active = !step.done && step === next;
          return (
            <div
              className={
                step.done ? "ladder-card ladder-done" : active ? "ladder-card ladder-next" : "ladder-card"
              }
              key={step.need}
            >
              <div className="ladder-need">{step.need}</div>
              <div className="muted small">{step.need === 1 ? "друг" : "друзей"}</div>
              <div className="ladder-reward">
                {step.coins > 0 && <span>{money(step.coins)}</span>}
                {step.energy > 0 && <span className="energy-text">⚡{step.energy}</span>}
                {step.gems > 0 && <span className="gems-text">◆{step.gems}</span>}
              </div>
              <div className="ladder-state">{step.done ? "получено" : "награда"}</div>
            </div>
          );
        })}
      </div>

      <div className="card muted small">
        {next
          ? `Ещё ${next.need - friends.invites} до награды «${next.title}»`
          : "Все награды за друзей получены"}
      </div>

      <div className="panel tip">
        <h3>Как это работает</h3>
        <p>
          Друг приходит по твоей ссылке и остаётся в игре. За каждого нового друга начисляется
          награда ступени и энергия, а билеты падают на третьем, пятом и десятом друге.
        </p>
      </div>

      <button className="btn btn-primary btn-lg" onClick={invite}>
        Пригласить друга
      </button>

      <div className="section-head">
        <h2>Лидеры</h2>
        <span className="muted small">по гаражам</span>
      </div>

      <div className="task-list">
        {top.map((item, index) => (
          <article
            className={item.user_id === selfId ? "card rating-row rating-self" : "card rating-row"}
            key={item.user_id}
          >
            <span className={index < 3 ? "rating-rank rating-top" : "rating-rank"}>{index + 1}</span>
            <div className="rating-name">
              <div>{nameOf(item)}</div>
              <div className="muted small">{item.plates} номеров</div>
            </div>
            <span className="price">{money(item.total)}</span>
          </article>
        ))}
        {!top.length && <div className="card muted small">Пока пусто</div>}
      </div>
    </section>
  );
}
