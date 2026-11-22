import { useEffect, useState } from "react";
import { api, tg } from "../api";
import { money } from "../format";
import { rarityColor, rarityLabel } from "../rarity";
import type { Offer, ShopData } from "../types";
import { Plate } from "./Plate";

type Tab = "numbers" | "energy" | "tickets";

const TABS: { id: Tab; label: string }[] = [
  { id: "numbers", label: "Номера" },
  { id: "energy", label: "Энергия" },
  { id: "tickets", label: "Билеты" },
];

const TICKETS = ["rare", "epic", "legendary"];

export function ShopView({
  refresh,
  notify,
}: {
  refresh: () => Promise<void>;
  notify: (message: string, kind?: "ok" | "err") => void;
}) {
  const [data, setData] = useState<ShopData | null>(null);
  const [tab, setTab] = useState<Tab>("numbers");
  const [busy, setBusy] = useState<string | null>(null);

  async function load() {
    try {
      setData(await api.shop());
    } catch (error) {
      notify((error as Error).message, "err");
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function buy(offer: Offer) {
    if (busy) return;
    setBusy(offer.code);
    try {
      const response = await api.buy(offer.code);

      if (response.invoice_url && tg?.openInvoice) {
        tg.openInvoice(response.invoice_url, (status) => {
          if (status === "paid") {
            notify("Оплачено, номер в гараже", "ok");
            void Promise.all([load(), refresh()]);
          } else if (status === "failed") {
            notify("Платёж не прошёл", "err");
          }
        });
      } else if (response.dev) {
        notify("DEV: номер выдан без оплаты", "ok");
        await Promise.all([load(), refresh()]);
      } else {
        notify("Не удалось открыть счёт", "err");
      }
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setBusy(null);
    }
  }

  async function buyEnergy(pack: string, energy: number) {
    if (busy) return;
    setBusy(pack);
    try {
      await api.buyEnergy(pack);
      notify(`Энергия +${energy}`, "ok");
      await refresh();
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setBusy(null);
    }
  }

  async function buyTicket(rarity: string) {
    if (busy) return;
    setBusy(rarity);
    try {
      await api.buyTicket(rarity);
      notify(`${rarityLabel(rarity)} билет куплен`, "ok");
      await refresh();
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setBusy(null);
    }
  }

  if (!data) return <div className="view center muted">Загружаем магазин…</div>;

  return (
    <section className="view">
      <div className="section-head">
        <h2>Магазин</h2>
        <span className="muted small">номера обновляются ежедневно</span>
      </div>

      <div className="segmented">
        {TABS.map((item) => (
          <button
            key={item.id}
            className={tab === item.id ? "segment segment-active" : "segment"}
            onClick={() => setTab(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {tab === "numbers" && (
        <>
          <div className="shop-grid">
            {data.offers.map((offer) => {
              const color = rarityColor(offer.rarity);
              return (
                <article className="card shop-card" key={offer.code} style={{ borderColor: `${color}33` }}>
                  <Plate code={offer.code} size="sm" glow={color} />
                  <div className="shop-meta">
                    <span className="rarity" style={{ color }}>
                      {rarityLabel(offer.rarity)}
                    </span>
                    <span className="stars-price">{offer.stars} ★</span>
                  </div>
                  <button
                    className="btn btn-gold btn-sm"
                    onClick={() => buy(offer)}
                    disabled={busy === offer.code}
                  >
                    {busy === offer.code ? "…" : "Забрать"}
                  </button>
                </article>
              );
            })}
          </div>
          <p className="muted small">
            Номера за звёзды остаются в коллекции навсегда и не продаются за игровые рубли.
          </p>
        </>
      )}

      {tab === "energy" && (
        <div className="shop-grid">
          {data.energy_packs.map((pack) => (
            <article className="card shop-card" key={pack.code}>
              <span className="pack-value">⚡ {pack.energy}</span>
              <span className="price">{money(pack.price)}</span>
              <button
                className="btn btn-primary btn-sm"
                onClick={() => buyEnergy(pack.code, pack.energy)}
                disabled={busy === pack.code}
              >
                {busy === pack.code ? "…" : "Купить"}
              </button>
            </article>
          ))}
        </div>
      )}

      {tab === "tickets" && (
        <div className="shop-grid">
          {TICKETS.map((rarity) => {
            const price = data.ticket_prices[rarity] ?? 0;
            return (
              <article className="card shop-card" key={rarity}>
                <span className="pack-value" style={{ color: rarityColor(rarity) }}>
                  {rarityLabel(rarity)}
                </span>
                <span className="muted small">один билет</span>
                <span className="price">{money(price)}</span>
                <button
                  className="btn btn-primary btn-sm"
                  onClick={() => buyTicket(rarity)}
                  disabled={busy === rarity}
                >
                  {busy === rarity ? "…" : "Купить"}
                </button>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
