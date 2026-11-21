import { useEffect, useState } from "react";
import { api } from "../api";
import { rarityColor, rarityLabel } from "../rarity";
import type { PlateT } from "../types";
import { Plate } from "./Plate";

export function GarageView({
  refresh,
  notify,
}: {
  refresh: () => Promise<void>;
  notify: (message: string, kind?: "ok" | "err") => void;
}) {
  const [plates, setPlates] = useState<PlateT[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<number | null>(null);

  async function load() {
    setLoading(true);
    try {
      const data = await api.garage();
      setPlates(data.plates);
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

  async function sell(plate: PlateT) {
    if (busy !== null) return;
    setBusy(plate.id);
    try {
      const response = await api.sell(plate.id);
      setPlates((list) => list.filter((item) => item.id !== plate.id));
      notify(`Номер ${plate.code} продан за ${response.amount} монет`, "ok");
      await refresh();
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setBusy(null);
    }
  }

  if (loading) return <div className="view center muted">Загружаем гараж…</div>;

  if (plates.length === 0) {
    return (
      <section className="view">
        <div className="empty panel">
          <div className="empty-plate">А000АА77</div>
          <h3>Гараж пуст</h3>
          <p>Первый номер появится после спина. Бесплатный — уже сейчас.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="view">
      <div className="section-head">
        <h2>Гараж</h2>
        <span className="muted">{plates.length} шт.</span>
      </div>

      <div className="garage-grid">
        {plates.map((plate) => {
          const color = rarityColor(plate.rarity);
          return (
            <article className="card plate-card" key={plate.id} style={{ borderColor: `${color}33` }}>
              <Plate code={plate.code} size="sm" />
              <div className="plate-card-foot">
                <span className="rarity" style={{ color }}>
                  {rarityLabel(plate.rarity)}
                </span>
                <span className="price">{plate.price.toLocaleString("ru-RU")}</span>
              </div>
              {plate.is_paid ? (
                <span className="badge">куплен за звёзды</span>
              ) : (
                <button
                  className="btn btn-ghost btn-sm"
                  onClick={() => sell(plate)}
                  disabled={busy === plate.id}
                >
                  {busy === plate.id ? "…" : "Продать"}
                </button>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
