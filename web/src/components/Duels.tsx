import { useEffect, useState } from "react";
import { api } from "../api";
import { money } from "../format";
import { rarityColor } from "../rarity";
import type { DuelT, JoinResult } from "../types";
import { Plate } from "./Plate";

const BETS = [100, 250, 500, 1000];

const STATUS_LABEL: Record<string, string> = {
  open: "ждёт соперника",
  finished: "завершён",
  tie: "ничья",
  cancelled: "отменён",
};

export function DuelsView({
  coins,
  selfId,
  refresh,
  notify,
}: {
  coins: number;
  selfId: number;
  refresh: () => Promise<void>;
  notify: (message: string, kind?: "ok" | "err") => void;
}) {
  const [open, setOpen] = useState<DuelT[]>([]);
  const [mine, setMine] = useState<DuelT[]>([]);
  const [bet, setBet] = useState(100);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<JoinResult | null>(null);

  async function load() {
    try {
      const data = await api.duels();
      setOpen(data.open);
      setMine(data.mine);
    } catch (error) {
      notify((error as Error).message, "err");
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function create() {
    if (busy) return;
    if (coins < bet) {
      notify("Не хватает денег на ставку", "err");
      return;
    }
    setBusy(true);
    try {
      await api.createDuel(bet);
      notify(`Дуэль на ${bet} создана`, "ok");
      await Promise.all([load(), refresh()]);
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setBusy(false);
    }
  }

  async function join(duel: DuelT) {
    if (busy) return;
    if (coins < duel.bet) {
      notify("Не хватает денег на эту дуэль", "err");
      return;
    }
    setBusy(true);
    try {
      const data = await api.joinDuel(duel.id);
      setResult(data);
      await Promise.all([load(), refresh()]);
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setBusy(false);
    }
  }

  async function cancel(duel: DuelT) {
    if (busy) return;
    setBusy(true);
    try {
      await api.cancelDuel(duel.id);
      notify("Ставка возвращена", "ok");
      await Promise.all([load(), refresh()]);
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="view">
      <div className="section-head">
        <h2>Дуэли</h2>
        <span className="muted">у кого номер дороже</span>
      </div>

      {result && (
        <div className="panel duel-result" onClick={() => setResult(null)}>
          <div className="duel-result-head" style={{ color: result.you_won ? "#c6ff3d" : "#ff7a8a" }}>
            {result.duel.status === "tie" ? "Ничья — ставки возвращены" : result.you_won ? "Победа" : "Поражение"}
          </div>
          <div className="duel-plates">
            <Plate code={result.plates[0].code} size="sm" glow={rarityColor(result.plates[0].rarity)} />
            <span className="vs">VS</span>
            <Plate code={result.plates[1].code} size="sm" glow={rarityColor(result.plates[1].rarity)} />
          </div>
          <div className="duel-prices">
            <span>{money(result.plates[0].price)}</span>
            <span>{money(result.plates[1].price)}</span>
          </div>
        </div>
      )}

      <div className="panel">
        <h3>Создать дуэль</h3>
        <div className="chips">
          {BETS.map((value) => (
            <button
              key={value}
              className={value === bet ? "chip chip-active" : "chip"}
              onClick={() => setBet(value)}
            >
              {value}
            </button>
          ))}
        </div>
        <button className="btn btn-primary" onClick={create} disabled={busy}>
          Поставить {money(bet)}
        </button>
      </div>

      <div className="section-head">
        <h3>Открытые</h3>
        <span className="muted">{open.length}</span>
      </div>

      {open.length === 0 ? (
        <p className="muted small">Пока никто не ждёт соперника. Создай дуэль первым.</p>
      ) : (
        <div className="list">
          {open.map((duel) => (
            <div className="row" key={duel.id}>
              <div>
                <div className="row-title">@{duel.creator ?? "игрок"}</div>
                <div className="muted small">ставка {duel.bet}</div>
              </div>
              {duel.creator_id === selfId ? (
                <button className="btn btn-ghost btn-sm" onClick={() => cancel(duel)} disabled={busy}>
                  Отменить
                </button>
              ) : (
                <button className="btn btn-primary btn-sm" onClick={() => join(duel)} disabled={busy}>
                  Принять
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="section-head">
        <h3>Мои матчи</h3>
      </div>

      {mine.length === 0 ? (
        <p className="muted small">История пока пуста.</p>
      ) : (
        <div className="list">
          {mine.map((duel) => (
            <div className="row" key={duel.id}>
              <div>
                <div className="row-title">
                  {duel.creator_id === selfId ? "ты" : `@${duel.creator ?? "игрок"}`} · {duel.bet}
                </div>
                <div className="muted small">{STATUS_LABEL[duel.status] ?? duel.status}</div>
              </div>
              {duel.status === "finished" && (
                <span className={duel.winner_id === selfId ? "win" : "lose"}>
                  {duel.winner_id === selfId ? "победа" : "поражение"}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
