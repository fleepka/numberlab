import { useEffect, useState } from "react";
import { api } from "../api";
import { money } from "../format";
import { rarityColor } from "../rarity";
import type { PlateT, TicketT } from "../types";
import { Plate } from "./Plate";

export function TicketsView({
  refresh,
  notify,
}: {
  refresh: () => Promise<void>;
  notify: (message: string, kind?: "ok" | "err") => void;
}) {
  const [items, setItems] = useState<TicketT[] | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [result, setResult] = useState<PlateT | null>(null);

  async function load() {
    try {
      setItems((await api.tickets()).items);
    } catch (error) {
      notify((error as Error).message, "err");
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function open(ticket: TicketT) {
    if (busy || ticket.count < 1) return;
    setBusy(ticket.rarity);
    try {
      const response = await api.useTicket(ticket.rarity);
      setResult(response.plate);
      notify(`${ticket.label} билет: ${response.plate.code} за ${money(response.plate.price)}`, "ok");
      await Promise.all([load(), refresh()]);
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setBusy(null);
    }
  }

  if (!items) return <div className="view center muted">Достаём билеты…</div>;

  const total = items.reduce((sum, item) => sum + item.count, 0);

  return (
    <section className="view">
      <div className="section-head">
        <h2>Билеты</h2>
        <span className="muted small">{total} шт.</span>
      </div>

      <div className="panel tip">
        <h3>Как это работает</h3>
        <p>
          Билет даёт одну бесплатную прокрутку номера своей редкости. Билеты падают за задания,
          охоту дня и пропуск сезона.
        </p>
      </div>

      {result && (
        <div className="card ticket-result">
          <span className="muted small">Последний билет</span>
          <Plate code={result.code} size="md" glow={rarityColor(result.rarity)} />
          <span className="price">{money(result.price)}</span>
        </div>
      )}

      <div className="ticket-grid">
        {items.map((ticket) => (
          <button
            key={ticket.rarity}
            className={ticket.count > 0 ? "ticket-card ticket-active" : "ticket-card"}
            onClick={() => open(ticket)}
            disabled={ticket.count < 1 || busy !== null}
          >
            <span className="ticket-count" style={{ color: rarityColor(ticket.rarity) }}>
              {ticket.count}
            </span>
            <span className="ticket-label" style={{ color: rarityColor(ticket.rarity) }}>
              {ticket.label}
            </span>
            <span className="muted small">
              {busy === ticket.rarity ? "крутим…" : ticket.count > 0 ? "открыть" : "нет билетов"}
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}
