import { useEffect, useState } from "react";
import { api } from "../api";
import type { GiftsData } from "../types";

export function GiftsView({
  refresh,
  notify,
}: {
  refresh: () => Promise<void>;
  notify: (message: string, kind?: "ok" | "err") => void;
}) {
  const [data, setData] = useState<GiftsData | null>(null);
  const [amounts, setAmounts] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState<number | null>(null);

  async function load() {
    try {
      setData(await api.gifts());
    } catch (error) {
      notify((error as Error).message, "err");
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function send(friendId: number) {
    if (busy !== null) return;
    const amount = Number(amounts[friendId] ?? 1);
    if (!Number.isFinite(amount) || amount < 1) {
      notify("Укажи количество кристаллов", "err");
      return;
    }
    setBusy(friendId);
    try {
      const result = await api.sendGift(friendId, Math.floor(amount));
      notify(`Подарок отправлен: ◆${result.amount}`, "ok");
      setAmounts((current) => ({ ...current, [friendId]: "" }));
      await Promise.all([load(), refresh()]);
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setBusy(null);
    }
  }

  if (!data) return <div className="view center muted">Загружаем подарки…</div>;

  return (
    <section className="view">
      <div className="section-head">
        <h2>Подарки</h2>
        <span className="muted small">осталось {data.left} из 3</span>
      </div>

      <div className="card">
        <p className="muted small">
          Дари друзьям кристаллы: от 1 до {data.max} ◆ за раз, не больше трёх подарков в день.
        </p>
      </div>

      {data.items.length === 0 ? (
        <div className="empty">
          <span className="empty-plate">🎁</span>
          <span>Пока нет друзей. Пригласи друга — и здесь появится, кому дарить.</span>
        </div>
      ) : (
        <div className="list">
          {data.items.map((friend) => (
            <div className="gift-row" key={friend.user_id}>
              <div>
                <div className="row-title">{friend.name}</div>
                <div className="muted small">LVL {friend.level}</div>
              </div>
              <div className="gift-controls">
                <input
                  className="gift-input"
                  type="number"
                  min={1}
                  max={data.max}
                  inputMode="numeric"
                  value={amounts[friend.user_id] ?? ""}
                  placeholder="1"
                  onChange={(event) =>
                    setAmounts((current) => ({
                      ...current,
                      [friend.user_id]: event.target.value,
                    }))
                  }
                />
                <button
                  className="btn btn-primary btn-sm"
                  onClick={() => send(friend.user_id)}
                  disabled={busy !== null || data.left <= 0}
                >
                  {busy === friend.user_id ? "…" : "Подарить"}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
