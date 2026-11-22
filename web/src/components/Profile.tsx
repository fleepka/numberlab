import { useEffect, useState } from "react";
import { api, tg } from "../api";
import { money } from "../format";
import { rarityColor, rarityLabel } from "../rarity";
import type { PlateT, Product, RankT, Tx, UserT } from "../types";
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
  { key: "pass", title: "Сезонный пропуск", hint: "награды сезона" },
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
  rank,
  top,
  refresh,
  notify,
  onNavigate,
}: {
  user: UserT;
  garageCount: number;
  rank: RankT;
  top: PlateT[];
  refresh: () => Promise<void>;
  notify: (message: string, kind?: "ok" | "err") => void;
  onNavigate?: (tab: "shop" | "pass" | "admin" | "settings") => void;
}) {
  const [history, setHistory] = useState<Tx[]>([]);
  const [dailyBusy, setDailyBusy] = useState(false);
  const [products, setProducts] = useState<Product[]>([]);
  const [buying, setBuying] = useState<string | null>(null);
  const [promo, setPromo] = useState("");

  async function redeemPromo() {
    const code = promo.trim();
    if (!code) return;
    try {
      const result = await api.redeemPromo(code);
      notify(`Промокод ${result.code} активирован`, "ok");
      setPromo("");
      await refresh();
    } catch (error) {
      notify((error as Error).message, "err");
    }
  }

  useEffect(() => {
    api
      .products()
      .then((data) => setProducts(data.items))
      .catch(() => undefined);
  }, []);

  async function buyProduct(code: string) {
    if (buying) return;
    setBuying(code);
    try {
      const result = await api.buyProduct(code);
      if (result.invoice_url && tg?.openInvoice) {
        tg.openInvoice(result.invoice_url, (status) => {
          if (status === "paid") {
            notify("Куплено", "ok");
            void refresh();
          }
        });
      } else if (result.dev) {
        notify("DEV: товар выдан без оплаты", "ok");
        await refresh();
      } else {
        notify("Не удалось открыть счёт", "err");
      }
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setBuying(null);
    }
  }

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

      <div className="card rank-card">
        <div className="rank-top">
          <span className="muted small">Ранг коллекции</span>
          <span className="rank-title">{rank.title}</span>
        </div>
        <div className="progress">
          <div className="progress-fill" style={{ width: `${rank.progress}%` }} />
        </div>
        <span className="muted small">
          {rank.next
            ? `${money(rank.total)} · до «${rank.next_title}» ${money(rank.next - rank.total)}`
            : `${money(rank.total)} · максимальный ранг`}
        </span>
      </div>

      <button className="btn btn-primary" onClick={claimDaily} disabled={dailyBusy}>
        {dailyBusy ? "…" : "Забрать ежедневную награду"}
      </button>

      <div className="card vip-card">
        <div className="section-head">
          <h3>VIP+</h3>
          {user.vip_until && <span className="badge">до {user.vip_until}</span>}
        </div>
        <ul className="vip-list">
          <li>+2 места в гараже</li>
          <li>Доход гаража ×1,5</li>
          <li>30 дней, продлевается в любой момент</li>
        </ul>
        <button className="btn btn-primary" onClick={() => buyProduct("vip")} disabled={buying !== null}>
          {buying === "vip" ? "…" : "Оформить VIP+ · 99 ★"}
        </button>
      </div>

      {products.some((item) => item.kind === "style" || item.kind === "plate") && (
        <>
          <div className="section-head">
            <h3>Косметика</h3>
            <span className="muted small">за звёзды</span>
          </div>
          <div className="shop-grid">
            {products
              .filter((item) => item.kind === "style" || item.kind === "plate")
              .map((item) => {
                const plate = item.kind === "plate";
                const equipped = plate
                  ? user.plate_skin === item.code.slice(6)
                  : user.frame === item.code.slice(6);
                return (
                  <article className="card shop-card" key={item.code}>
                    <span
                      className={plate ? "plate-swatch" : "frame-preview"}
                      style={{
                        borderColor: item.color ?? "#ffc247",
                        background: plate && item.color ? `${item.color}22` : undefined,
                      }}
                    >
                      {plate ? "номер" : "рамка"}
                    </span>
                    <span className="stars-price">{item.stars} ★</span>
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={() => buyProduct(item.code)}
                      disabled={buying !== null}
                    >
                      {buying === item.code ? "…" : equipped ? "надето" : "Купить"}
                    </button>
                  </article>
                );
              })}
          </div>
        </>
      )}

      <div className="card">
        <div className="section-head">
          <h3>Промокод</h3>
        </div>
        <div className="chips">
          <input
            className="chat-input bid-input"
            value={promo}
            placeholder="Введи промокод"
            onChange={(event) => setPromo(event.target.value)}
          />
          <button
            className="btn btn-primary btn-sm"
            onClick={redeemPromo}
            disabled={!promo.trim()}
          >
            Активировать
          </button>
        </div>
      </div>

      <div className="menu-list">
        {(user.is_admin
          ? [...MENU, { key: "admin", title: "Админка", hint: "игроки и выдача" }]
          : MENU
        ).map((item) => (
          <button
            className="menu-row"
            key={item.key}
            onClick={() =>
              item.key === "shop" ||
              item.key === "pass" ||
              item.key === "admin" ||
              item.key === "settings"
                ? onNavigate?.(item.key)
                : notify("Скоро добавим", "ok")
            }
          >
            <span className="menu-title">{item.title}</span>
            <span className="menu-hint">{item.hint}</span>
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
