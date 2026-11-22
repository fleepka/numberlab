import { useEffect, useRef, useState } from "react";
import { api, tg } from "../api";
import { daysLeftInMonth, money } from "../format";
import { formatTime, rarityColor, rarityLabel } from "../rarity";
import type { PlateT, UserT } from "../types";
import { Plate } from "./Plate";

const LETTERS = "АВЕКМНОРСТУХ";
const REGIONS = ["77", "50", "99", "01", "78", "97", "199", "777", "97"];

const LINKS = [
  { id: "shop", label: "Витрина", hint: "номера за Stars" },
  { id: "collections", label: "Коллекции", hint: "награды за наборы" },
  { id: "duels", label: "Дуэли", hint: "1 на 1 на монеты" },
] as const;

type NextTab = (typeof LINKS)[number]["id"] | "garage";

function pick(source: string): string {
  return source[Math.floor(Math.random() * source.length)];
}

function previewCode(): string {
  const digits = String(Math.floor(Math.random() * 1000)).padStart(3, "0");
  const region = REGIONS[Math.floor(Math.random() * REGIONS.length)];
  return pick(LETTERS) + digits + pick(LETTERS) + pick(LETTERS) + region;
}

export function SpinView({
  user,
  refresh,
  notify,
  onNavigate,
}: {
  user: UserT;
  refresh: () => Promise<void>;
  notify: (message: string, kind?: "ok" | "err") => void;
  onNavigate?: (tab: NextTab) => void;
}) {
  const [rolling, setRolling] = useState(false);
  const [preview, setPreview] = useState(previewCode);
  const [result, setResult] = useState<PlateT | null>(null);
  const [selling, setSelling] = useState(false);
  const [readyIn, setReadyIn] = useState(user.energy_in);
  const interval = useRef<number | null>(null);

  useEffect(() => setReadyIn(user.energy_in), [user.energy_in]);

  useEffect(() => {
    if (readyIn <= 0) return;
    const timer = window.setInterval(() => setReadyIn((value) => Math.max(0, value - 1)), 1000);
    return () => window.clearInterval(timer);
  }, [readyIn]);

  useEffect(() => () => {
    if (interval.current) window.clearInterval(interval.current);
  }, []);

  const free = user.energy > 0;
  const cost = free ? 0 : 50;

  async function roll() {
    if (rolling) return;
    if (!free && user.coins < cost) {
      notify("Энергии нет, а монет на крутку не хватает", "err");
      return;
    }

    setRolling(true);
    setResult(null);
    interval.current = window.setInterval(() => setPreview(previewCode()), 55);
    const started = Date.now();

    try {
      const response = await api.spin();
      const wait = Math.max(0, 900 - (Date.now() - started));
      await new Promise((resolve) => setTimeout(resolve, wait));
      setPreview(response.plate.code);
      setResult(response.plate);
      setReadyIn(response.energy_in);
      tg?.HapticFeedback?.impactOccurred("medium");
      await refresh();
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      if (interval.current) window.clearInterval(interval.current);
      setRolling(false);
    }
  }

  async function sellResult() {
    if (!result || selling) return;
    setSelling(true);
    try {
      const response = await api.sell(result.id);
      notify(`Номер ${result.code} продан за ${money(response.amount)}`, "ok");
      setResult(null);
      await refresh();
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setSelling(false);
    }
  }

  function share() {
    if (!result) return;
    const text = `Мой номер ${result.code} стоит ${money(result.price)} в NUMBERLAB`;
    const url = `https://t.me/share/url?url=${encodeURIComponent("https://t.me/NumbersLab_bot/app")}&text=${encodeURIComponent(text)}`;
    if (tg?.openTelegramLink) tg.openTelegramLink(url);
    else window.open(url, "_blank");
  }

  const color = result ? rarityColor(result.rarity) : "#f5c451";

  return (
    <section className="view">
      <div className="season-row">
        <span className="season-pill">🏆 Сезон 1 · ещё {daysLeftInMonth()} д</span>
        <span className="country-pill">🇷🇺 RUS</span>
      </div>

      <div className="stage">
        <div className="stage-glow" style={{ background: color }} />
        <div className={rolling ? "reel reel-spinning" : "reel"}>
          <Plate code={rolling ? preview : result?.code ?? preview} size="lg" glow={rolling ? undefined : color} />
        </div>

        {result ? (
          <div className="result" key={result.id}>
            <span className="result-rarity" style={{ color }}>
              {rarityLabel(result.rarity)}
            </span>
            <span className="result-price">{money(result.price)}</span>
            {result.factors && result.factors.length > 0 && (
              <div className="factor-chips">
                {result.factors.map((factor) => (
                  <span className="chip" key={factor.title}>
                    {factor.title} ×{factor.points}
                  </span>
                ))}
              </div>
            )}
            <button className="share-btn" onClick={share}>
              Поделиться ↗
            </button>
          </div>
        ) : (
          <p className="stage-hint">
            {rolling ? "Крутим…" : "Крути номер и собирай коллекцию"}
          </p>
        )}
      </div>

      <div className="result-actions">
        <button
          className="btn btn-ghost"
          onClick={() => onNavigate?.("garage")}
          disabled={!result || rolling}
        >
          В гараж
        </button>
        <button className="btn btn-ghost" onClick={sellResult} disabled={!result || selling}>
          {selling ? "…" : "Продать"}
        </button>
      </div>

      <button className="btn btn-primary btn-lg" onClick={roll} disabled={rolling}>
        {rolling ? "Крутим…" : free ? "Крутить · ⚡1" : `Крутить · ${money(cost)}`}
      </button>

      <div className="energy-line">
        <span>⚡ {user.energy}</span>
        <span className="dot" />
        {user.energy >= user.energy_max ? (
          <span>энергия полная</span>
        ) : (
          <span>+1 через {formatTime(readyIn)}</span>
        )}
        <span className="dot" />
        <span className="muted">номеров: {user.spins}</span>
      </div>

      {onNavigate && (
        <div className="link-row">
          {LINKS.map((link) => (
            <button className="link-card" key={link.id} onClick={() => onNavigate(link.id)}>
              <span className="link-label">{link.label}</span>
              <span className="muted small">{link.hint}</span>
            </button>
          ))}
        </div>
      )}

      <div className="panel tip">
        <h3>Как это работает</h3>
        <p>
          Цена номера зависит от рисунка: три одинаковые цифры, последовательности, повтор букв
          и код региона повышают редкость. Проданный номер приносит деньги, редкие попадают в ленту.
        </p>
      </div>
    </section>
  );
}
