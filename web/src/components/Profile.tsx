import { useEffect, useState } from "react";
import { api } from "../api";
import { rarityColor, rarityLabel } from "../rarity";
import type { PlateT, Tx, UserT } from "../types";
import { Plate } from "./Plate";

const REASONS: Record<string, string> = {
  spin: "спин",
  sell: "продажа номера",
  daily: "ежедневная награда",
  collection: "награда за коллекцию",
  duel_bet: "ставка в дуэли",
  duel_win: "выигрыш в дуэли",
  duel_refund: "возврат ставки",
};

const MENU = [
  { key: "pass", title: "Сезонный пропуск", hint: "" },
  { key: "shop", title: "Магазин", hint: "номера и награды" },
  { key: "promo", title: "Промокод", hint: "ввести код" },
  { key: "settings", title: "Настройки", hint: "профиль и уведомления" },
  { key: "rules", title: "Правила игры", hint: "" },
  { key: "support", title: "Поддержка", hint: "" },
] as const;

function signed(value: number, currency: string): string {
  const mark = currency === "gems" ? " ◆" : "";
  return `${value > 0 ? "+" : ""}${value.toLocaleString("ru-RU")}${mark}`;
}

export function ProfileView({
  user,
  garageCount,
  top,
  refresh,
  notify,
  onNavigate,
}: {
  user: UserT;
  garageCount: number;
  top: PlateT[];
  refresh: () => Promise<void>;
  notify: (message: string, kind?: "ok" | "err") => void;
  onNavigate?: (tab: "shop") => void;
}) {
  const [history, setHistory] = useState<Tx[]>([]);
  const [dailyBusy, setDailyBusy] = useState(false);

  useEffect(() => {
    api
      .history()
      .then((data) => setHistory(data.items))
      .catch((error) => notify((error as Error).message, "err"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function claimDaily() {
    if (dailyBusy) return;
    setDailyBusy(true);
    try {
      const response = await api.daily();
      notify(`Награда: +${response.amount} ₽, серия ${response.streak}`, "ok");
      await refresh();
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setDailyBusy(false);
    }
  }

  const total = user.duels_won + user.duels_lost;
  const xpPercent =
    user.xp_to_next > 0 ? Math.max(0, 100 - Math.round((user.xp_to_next / 400) * 100)) : 100;

  return (
    <section className="view">
      <div className="panel profile-head">
        <div className="avatar">
          {user.photo_url ? (
            <img src={user.photo_url} alt="" />
          ) : (
            (user.first_name || "N").slice(0, 1).toUpperCase()
          )}
        </div>
        <div className="profile-id">
          <h2>{user.first_name || "Игрок"}</h2>
          <span className="muted">@{user.username ?? "—"} · id {user.tg_id}</span>
        </div>
        <span className="level-badge">LVL {user.level}</span>
      </div>

      <div className="panel level-card">
        <div className="level-top">
          <span className="muted small">{user.xp} XP</span>
          <span className="muted small">
            {user.xp_to_next > 0 ? `до ${user.level + 1} уровня ${user.xp_to_next} XP` : "максимум"}
          </span>
        </div>
        <div className="progress">
          <div className="progress-fill" style={{ width: `${xpPercent}%` }} />
        </div>
      </div>

      <div className="stat-grid">
        <div className="stat">
          <span className="stat-value">{user.coins.toLocaleString("ru-RU")}</span>
          <span className="stat-label">₽</span>
        </div>
        <div className="stat">
          <span className="stat-value stat-gems">{user.gems} ◆</span>
          <span className="stat-label">GEMS</span>
        </div>
        <div className="stat">
          <span className="stat-value">{garageCount}</span>
          <span className="stat-label">в гараже</span>
        </div>
        <div className="stat">
          <span className="stat-value">{total ? Math.round((user.duels_won / total) * 100) : 0}%</span>
          <span className="stat-label">винрейт</span>
        </div>
      </div>

      <button className="btn btn-primary" onClick={claimDaily} disabled={dailyBusy}>
        {dailyBusy ? "…" : "Забрать ежедневную награду"}
      </button>

      <div className="menu-list">
        {MENU.map((item) => (
          <button
            className="menu-row"
            key={item.key}
            onClick={() =>
              item.key === "shop" ? onNavigate?.("shop") : notify("Скоро добавим", "ok")
            }
          >
            <span className="menu-title">{item.title}</span>
            <span className="menu-hint">{item.key === "pass" ? `${user.level} / 30` : item.hint}</span>
            <span className="menu-chevron">›</span>
          </button>
        ))}
      </div>

      {top.length > 0 && (
        <>
          <div className="section-head">
            <h3>Лучшие номера</h3>
          </div>
          <div className="top-strip">
            {top.map((plate) => (
              <Plate key={plate.id} code={plate.code} size="sm" glow={rarityColor(plate.rarity)} />
            ))}
          </div>
        </>
      )}

      <div className="section-head">
        <h3>История операций</h3>
      </div>

      {history.length === 0 ? (
        <p className="muted small">Операций пока нет.</p>
      ) : (
        <div className="list">
          {history.map((tx) => (
            <div className="row" key={tx.id}>
              <div>
                <div className="row-title">
                  {REASONS[tx.reason] ?? tx.reason}
                  {tx.ref && tx.reason === "sell" ? ` · ${tx.ref}` : ""}
                </div>
                {tx.ref && tx.reason !== "sell" && <div className="muted small">{tx.ref}</div>}
              </div>
              <span className={tx.delta >= 0 ? "win" : "lose"}>{signed(tx.delta, tx.currency)}</span>
            </div>
          ))}
        </div>
      )}

      <p className="muted small">
        Редкость последнего номера: {top[0] ? rarityLabel(top[0].rarity) : "—"}
      </p>
    </section>
  );
}
