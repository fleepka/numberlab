import { useEffect, useState } from "react";
import { api } from "../api";
import { money } from "../format";
import { rarityColor, rarityLabel } from "../rarity";
import type { GarageData, PlateT } from "../types";
import { Plate } from "./Plate";

const CRAFT_TARGET: Record<string, string> = {
  common: "Редкий",
  rare: "Эпический",
  epic: "Легендарный",
  legendary: "Мифический",
  mythic: "Мифический",
};

export function GarageView({
  refresh,
  notify,
}: {
  refresh: () => Promise<void>;
  notify: (message: string, kind?: "ok" | "err") => void;
}) {
  const [data, setData] = useState<GarageData | null>(null);
  const [selected, setSelected] = useState<number[]>([]);
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      setData(await api.garage());
    } catch (error) {
      notify((error as Error).message, "err");
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function toggle(plate: PlateT) {
    if (plate.is_paid) return;
    setSelected((list) =>
      list.includes(plate.id) ? list.filter((id) => id !== plate.id) : [...list, plate.id],
    );
  }

  async function sellSelected() {
    if (!selected.length || busy) return;
    setBusy(true);
    try {
      const result = await api.sellMany(selected);
      notify(`Продано ${result.sold} номеров за ${money(result.amount)}`, "ok");
      setSelected([]);
      await Promise.all([load(), refresh()]);
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setBusy(false);
    }
  }

  async function claimIncome() {
    if (busy) return;
    setBusy(true);
    try {
      const result = await api.collectIncome();
      notify(`Доход гаража: ${money(result.amount)}`, "ok");
      await Promise.all([load(), refresh()]);
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setBusy(false);
    }
  }

  async function craftSelected() {
    if (!selected.length || busy) return;
    setBusy(true);
    try {
      const result = await api.craft(selected);
      notify(
        `Крафт: ${result.target_label} ${result.plate.code} за ${money(result.value)}`,
        "ok",
      );
      setSelected([]);
      await Promise.all([load(), refresh()]);
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setBusy(false);
    }
  }

  if (!data) return <div className="view center muted">Загружаем гараж…</div>;

  const { plates, income } = data;
  const slots = data.slots;

  async function buySlots() {
    if (busy) return;
    setBusy(true);
    try {
      await api.buySlots();
      notify("Гараж расширен на 5 мест", "ok");
      await Promise.all([load(), refresh()]);
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setBusy(false);
    }
  }
  const selectedSum = plates
    .filter((plate) => selected.includes(plate.id))
    .reduce((sum, plate) => sum + plate.price, 0);

  if (!plates.length) {
    return (
      <section className="view">
        <div className="empty panel">
          <div className="empty-plate">А000АА77</div>
          <h3>Гараж пуст</h3>
          <p className="muted small">Первый номер появится после прокрутки — энергия на первую уже есть.</p>
        </div>
      </section>
    );
  }

  const best = plates[0];
  const selectedPlates = plates.filter((plate) => selected.includes(plate.id));
  const sameRarity =
    selectedPlates.length > 0 && new Set(selectedPlates.map((plate) => plate.rarity)).size === 1;
  const craftable =
    selectedPlates.length >= 3 && selectedPlates.length <= 7 && sameRarity && !selectedPlates.some((plate) => plate.is_paid);
  const craftTarget = craftable ? CRAFT_TARGET[selectedPlates[0].rarity] : null;

  return (
    <section className="view">
      <div className="card garage-summary">
        <div className="garage-summary-top">
          <div>
            <div className="muted small">Стоимость гаража</div>
            <div className="garage-total">{money(income.total)}</div>
          </div>
          <span className="badge">
            {plates.length} / {slots} мест
          </span>
        </div>

        <div className="income-row">
          <div>
            <div className="muted small">Доход гаража</div>
            <div className="income-rate">+{money(income.rate)} в час</div>
          </div>
          <div className="selection-actions">
            <button className="btn btn-ghost btn-sm" onClick={buySlots} disabled={busy}>
              +5 мест · 200 ◆
            </button>
            <button
              className="btn btn-primary btn-sm"
              onClick={claimIncome}
              disabled={busy || income.available <= 0}
            >
              {income.available > 0 ? `Забрать ${money(income.available)}` : "Копится"}
            </button>
          </div>
        </div>
      </div>

      <div className="garage-best" onClick={() => toggle(best)}>
        <Plate code={best.code} size="sm" country={best.country} glow={rarityColor(best.rarity)} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="muted small">Лучший номер</div>
          <div className="garage-best-code" style={{ color: rarityColor(best.rarity) }}>
            {rarityLabel(best.rarity)} · {money(best.price)}
          </div>
        </div>
      </div>

      <div className="panel tip">
        <h3>Крафт номера</h3>
        <p>
          Выбери 3–7 номеров одной редкости — получишь один номер следующей редкости. В половине
          случаев он дешевле суммы, в трети — примерно столько же, иногда дороже.
        </p>
      </div>

      <div className="section-head">
        <h2>Все номера</h2>
        <button
          className="ghost-link"
          onClick={() =>
            setSelected(selected.length === plates.filter((p) => !p.is_paid).length ? [] : plates.filter((p) => !p.is_paid).map((p) => p.id))
          }
        >
          {selected.length ? "Снять выбор" : "Выбрать все"}
        </button>
      </div>

      <div className="garage-grid">
        {plates.map((plate) => {
          const active = selected.includes(plate.id);
          return (
            <button
              className={
                active ? "plate-card plate-card-active" : plate.is_paid ? "plate-card plate-card-paid" : "plate-card"
              }
              key={plate.id}
              onClick={() => toggle(plate)}
            >
              <span className={active ? "pick pick-active" : "pick"}>{active ? "✓" : ""}</span>
              <Plate code={plate.code} size="sm" country={plate.country} glow={rarityColor(plate.rarity)} />
              <span className="plate-price" style={{ color: rarityColor(plate.rarity) }}>
                {money(plate.price)}
              </span>
              <span className="muted small">
                {plate.is_paid ? "за звёзды" : rarityLabel(plate.rarity)}
              </span>
            </button>
          );
        })}
      </div>

      {selected.length > 0 && (
        <div className="selection-bar">
          <div>
            <div className="selection-sum">{money(selectedSum)}</div>
            <div className="muted small">{selected.length} выбрано</div>
          </div>
          <div className="selection-actions">
            <button
              className="btn btn-ghost btn-sm"
              onClick={craftSelected}
              disabled={!craftable || busy}
              title={craftable ? "" : "3–7 номеров одной редкости"}
            >
              {craftTarget ? `В ${craftTarget}` : "Крафт"}
            </button>
            <button className="btn btn-primary btn-sm" onClick={sellSelected} disabled={busy}>
              {busy ? "…" : "Продать"}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
