import { useEffect, useState } from "react";
import { api, tg } from "../api";
import { money } from "../format";
import { rarityColor, rarityLabel } from "../rarity";
import type { AuctionData, Offer, ShopData } from "../types";
import { Plate } from "./Plate";

type Tab = "numbers" | "tickets" | "auction" | "style";

const TABS: { id: Tab; label: string }[] = [
  { id: "numbers", label: "Номера" },
  { id: "tickets", label: "Билеты" },
  { id: "auction", label: "Аукцион" },
  { id: "style", label: "Стиль" },
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
  const [auction, setAuction] = useState<AuctionData | null>(null);
  const [bidValue, setBidValue] = useState("");

  useEffect(() => {
    if (tab !== "auction") return;
    api
      .auction()
      .then((lot) => {
        setAuction(lot);
        setBidValue(String(lot.min_bid));
      })
      .catch((error: Error) => notify(error.message, "err"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  async function bid() {
    const amount = Number(bidValue);
    if (!auction || !Number.isFinite(amount) || busy) return;
    setBusy("auction");
    try {
      await api.bidAuction(amount);
      notify(`Ставка ${money(amount)} принята`, "ok");
      const lot = await api.auction();
      setAuction(lot);
      setBidValue(String(lot.min_bid));
      await refresh();
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setBusy(null);
    }
  }

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

  async function buyFrame(code: string) {
    if (busy) return;
    setBusy(code);
    try {
      await api.buyFrame(code);
      notify("Рамка применена", "ok");
      await Promise.all([load(), refresh()]);
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

      {tab === "auction" && (
        <div className="card vip-card">
          <div className="section-head">
            <h3>Аукцион сезона</h3>
            {auction && (
              <span className="badge">
                до {new Date(auction.ends_at).toLocaleString("ru-RU", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}
              </span>
            )}
          </div>

          {!auction ? (
            <p className="muted small">Открываем лот…</p>
          ) : (
            <>
              <div className="auction-lot">
                <Plate code={auction.code} size="md" glow={rarityColor(auction.rarity)} />
                <div className="price">
                  {auction.top_bid ? money(auction.top_bid) : `старт ${money(auction.min_bid)}`}
                </div>
                <div className="muted small">
                  {auction.leader ? `лидирует ${auction.leader}` : "ставок пока нет"}
                </div>
              </div>

              <input
                className="chat-input bid-input"
                type="number"
                inputMode="numeric"
                value={bidValue}
                onChange={(event) => setBidValue(event.target.value)}
              />

              <button className="btn btn-primary btn-lg" onClick={bid} disabled={busy === "auction"}>
                {busy === "auction" ? "…" : `Поставить ${bidValue ? money(Number(bidValue)) : ""}`}
              </button>
              <p className="muted small">
                Шаг {money(auction.step)}. Победитель забирает номер, ставки остальных возвращаются.
              </p>
            </>
          )}
        </div>
      )}

      {tab === "style" && (
        <div className="shop-grid">
          {data.frames.map((frame) => (
            <article className="card shop-card" key={frame.code}>
              <span className="frame-preview" style={{ borderColor: frame.color }}>
                {frame.title}
              </span>
              <span className="price">◆ {frame.price}</span>
              <button
                className="btn btn-primary btn-sm"
                onClick={() => buyFrame(frame.code)}
                disabled={busy === frame.code}
              >
                {busy === frame.code ? "…" : "Надеть"}
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
