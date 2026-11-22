import { useEffect, useState } from "react";
import { api, tg } from "../api";
import { money } from "../format";
import type { PassData, PassReward } from "../types";

function RewardChips({ reward }: { reward: PassReward }) {
  return (
    <span className="pass-rewards">
      {reward.coins > 0 && <span className="price">{money(reward.coins)}</span>}
      {reward.energy > 0 && <span className="energy-text">⚡{reward.energy}</span>}
      {reward.gems > 0 && <span className="gems-text">◆{reward.gems}</span>}
      {reward.ticket && <span className="badge">билет</span>}
    </span>
  );
}

export function PassView({
  notify,
  refresh,
}: {
  notify: (message: string, kind?: "ok" | "err") => void;
  refresh: () => Promise<void>;
}) {
  const [data, setData] = useState<PassData | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  async function load() {
    try {
      setData(await api.pass());
    } catch (error) {
      notify((error as Error).message, "err");
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function claim(level: number, track: "free" | "premium") {
    if (busy) return;
    setBusy(`${level}:${track}`);
    try {
      await api.claimPass(level, track);
      notify(`Уровень ${level}: награда получена`, "ok");
      await Promise.all([load(), refresh()]);
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setBusy(null);
    }
  }

  async function buy() {
    if (busy) return;
    setBusy("buy");
    try {
      const result = await api.buyPass();
      if (result.invoice_url) {
        tg?.openInvoice(result.invoice_url, () => undefined);
      } else {
        notify("Премиум-пропуск открыт", "ok");
        await Promise.all([load(), refresh()]);
      }
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setBusy(null);
    }
  }

  if (!data) return <div className="view center muted">Открываем пропуск…</div>;

  const next = (data.level + 1) * data.points_per_level;
  const progress = Math.min(100, Math.round((data.points / Math.max(1, next)) * 100));
  const visible = data.levels.filter((item) => item.level <= Math.max(data.level + 1, 3)).reverse();

  return (
    <section className="view">
      <div className="card pass-head">
        <div className="pass-level-row">
          <div>
            <div className="muted small">Сезонный пропуск</div>
            <div className="pass-level">
              ур. {data.level}
              <span className="muted small"> / {data.max_level}</span>
            </div>
          </div>
          {data.premium ? (
            <span className="badge pass-premium-badge">премиум</span>
          ) : (
            <button className="btn btn-primary btn-sm" onClick={buy} disabled={busy !== null}>
              {busy === "buy" ? "…" : `Премиум · ${data.price_stars} ★`}
            </button>
          )}
        </div>
        <div className="progress">
          <div className="progress-fill" style={{ width: `${progress}%` }} />
        </div>
        <div className="muted small">
          {data.points} очков · до следующего уровня {Math.max(0, next - data.points)}
        </div>
      </div>

      <div className="pass-list">
        {visible.map((item) => (
          <article className={item.unlocked ? "card pass-card" : "card pass-card pass-locked"} key={item.level}>
            <div className="pass-card-top">
              <span className="pass-card-level">Уровень {item.level}</span>
              <span className="muted small">{item.unlocked ? "открыт" : "закрыт"}</span>
            </div>

            <div className="pass-row">
              <span className="pass-track">Бесплатно</span>
              <RewardChips reward={item.free} />
              {item.free.claimed ? (
                <span className="badge">получено</span>
              ) : (
                <button
                  className="btn btn-ghost btn-sm"
                  disabled={!item.unlocked || busy !== null}
                  onClick={() => claim(item.level, "free")}
                >
                  {busy === `${item.level}:free` ? "…" : "Забрать"}
                </button>
              )}
            </div>

            <div className="pass-row pass-row-premium">
              <span className="pass-track">Премиум</span>
              <RewardChips reward={item.premium} />
              {item.premium.claimed ? (
                <span className="badge">получено</span>
              ) : (
                <button
                  className="btn btn-primary btn-sm"
                  disabled={!data.premium || !item.unlocked || busy !== null}
                  onClick={() => claim(item.level, "premium")}
                >
                  {busy === `${item.level}:premium` ? "…" : data.premium ? "Забрать" : "★"}
                </button>
              )}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
