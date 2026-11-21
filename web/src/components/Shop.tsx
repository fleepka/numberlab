import { useEffect, useState } from "react";
import { api, tg } from "../api";
import { rarityColor, rarityLabel } from "../rarity";
import type { Offer } from "../types";
import { Plate } from "./Plate";

export function ShopView({
  refresh,
  notify,
}: {
  refresh: () => Promise<void>;
  notify: (message: string, kind?: "ok" | "err") => void;
}) {
  const [offers, setOffers] = useState<Offer[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const data = await api.shop();
      setOffers(data.offers);
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

  if (loading) return <div className="view center muted">Загружаем витрину…</div>;

  return (
    <section className="view">
      <div className="section-head">
        <h2>Витрина</h2>
        <span className="muted">обновляется ежедневно</span>
      </div>

      <div className="shop-grid">
        {offers.map((offer) => {
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
        Номера за звёзды остаются в коллекции навсегда и не продаются за игровые монеты.
      </p>
    </section>
  );
}
