import { useEffect, useState } from "react";
import { api } from "../api";
import { money } from "../format";
import type { CollectionT } from "../types";

export function CollectionsView({
  refresh,
  notify,
}: {
  refresh: () => Promise<void>;
  notify: (message: string, kind?: "ok" | "err") => void;
}) {
  const [items, setItems] = useState<CollectionT[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<number | null>(null);

  async function load() {
    setLoading(true);
    try {
      const data = await api.collections();
      setItems(data.items);
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function claim(item: CollectionT) {
    if (busy !== null) return;
    setBusy(item.id);
    try {
      const result = await api.claimCollection(item.id);
      const parts = [`+${money(result.rewards.coins)}`];
      if (result.rewards.gems) parts.push(`+${result.rewards.gems} GEMS`);
      if (result.rewards.xp) parts.push(`+${result.rewards.xp} XP`);
      notify(`${item.title}: ${parts.join(", ")}`, "ok");
      await Promise.all([load(), refresh()]);
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setBusy(null);
    }
  }

  if (loading) return <div className="view center muted">Собираем коллекции…</div>;

  const done = items.filter((item) => item.claimed).length;

  return (
    <section className="view">
      <div className="section-head">
        <h2>Коллекции</h2>
        <span className="muted">
          {done} из {items.length}
        </span>
      </div>

      <div className="collection-list">
        {items.map((item) => {
          const percent = Math.min(100, Math.round((item.progress / item.target) * 100));
          return (
            <article className={item.claimed ? "card collection-card claimed" : "card collection-card"} key={item.id}>
              <div className="collection-head">
                <div>
                  <div className="collection-title">{item.title}</div>
                  <div className="muted small">{item.description}</div>
                </div>
                <span className="collection-count">
                  {item.progress}/{item.target}
                </span>
              </div>

              <div className="progress">
                <div
                  className={item.done ? "progress-fill progress-done" : "progress-fill"}
                  style={{ width: `${percent}%` }}
                />
              </div>

              <div className="collection-foot">
                <div className="rewards">
                  <span className="price">{money(item.reward_coins)}</span>
                  {item.reward_gems > 0 && <span className="gems-text">{item.reward_gems} ◆</span>}
                  <span className="muted small">{item.reward_xp} XP</span>
                </div>
                {item.claimed ? (
                  <span className="badge">получено</span>
                ) : (
                  <button
                    className="btn btn-primary btn-sm"
                    disabled={!item.done || busy === item.id}
                    onClick={() => claim(item)}
                  >
                    {busy === item.id ? "…" : "Забрать"}
                  </button>
                )}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
