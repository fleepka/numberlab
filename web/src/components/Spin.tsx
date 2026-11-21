import { useEffect, useRef, useState } from "react";
import { api, tg } from "../api";
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

type NextTab = (typeof LINKS)[number]["id"];

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

  const color = result ? rarityColor(result.rarity) : "#c6ff3d";

  return (
    <section className="view">
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
            <span className="result-price">+{result.price.toLocaleString("ru-RU")} монет</span>
          </div>
        ) : (
          <p className="stage-hint">
            {rolling ? "Крутим барабан…" : "Крути номер и собирай коллекцию"}
          </p>
        )}
      </div>

      <button className="btn btn-primary btn-lg" onClick={roll} disabled={rolling}>
        {rolling ? "Крутим…" : free ? "Крутить · ⚡1" : `Крутить · ${cost} монет`}
      </button>

      <div className="stage-meta">
        <span>
          ⚡ {user.energy}/{user.energy_max}
        </span>
        <span className="dot" />
        {user.energy >= user.energy_max ? (
          <span>Энергия полная</span>
        ) : (
          <span>+1 через {formatTime(readyIn)}</span>
        )}
        <span className="dot" />
        <span>Номеров: {user.spins}</span>
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

      {result && result.factors && result.factors.length > 0 && (
        <div className="panel factors">
          <h3>Почему такая цена</h3>
          <div className="factor-list">
            {result.factors.map((factor) => (
              <div className="factor" key={factor.title}>
                <span>{factor.title}</span>
                <span className="factor-points">+{factor.points}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="panel tip">
        <h3>Как это работает</h3>
        <p>
          Цена номера зависит от рисунка: три одинаковые цифры, последовательности, повтор букв
          и код региона повышают редкость. Проданный номер приносит монеты, редкие попадают в ленту.
        </p>
      </div>
    </section>
  );
}
