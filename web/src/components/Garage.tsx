import { useEffect, useState } from "react";
import { api } from "../api";
import { money } from "../format";
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
      notify(`Номер ${plate.code} продан за ${money(response.amount)}`, "ok");
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
          <p>Первый номер появится после крутки. Энергия на первую уже есть.</p>
        </div>
      </section>
    );
  }

  const total = plates.reduce((sum, plate) => sum + plate.price, 0);
  const best = plates.reduce((top, plate) => (plate.price > top.price ? plate : top), plates[0]);

  return (
    <section className="view">
      <div className="card garage-summary">
        <div className="garage-summary-top">
          <div>
            <div className="muted small">Стоимость гаража</div>
            <div className="garage-total">{money(total)}</div>
          </div>
          <span className="badge">{plates.length} номеров</span>
        </div>

        <div className="garage-best">
          <span className="muted small">Лучший номер</span>
          <span className="garage-best-code" style={{ color: rarityColor(best.rarity) }}>
            {best.code}
          </span>
          <span className="price">{money(best.price)}</span>
        </div>
      </div>

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
                <span className="price">{money(plate.price)}</span>
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
