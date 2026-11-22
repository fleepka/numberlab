import { useEffect, useState } from "react";
import { api } from "../api";
import type { ThemeItem } from "../types";

const RULES: { title: string; text: string }[] = [
  {
    title: "Как играть",
    text: "Жми «Крутить» — выпадает номер. Выбирай страну и редкость, плати энергией или рублями. Номер можно оставить в гараже или продать.",
  },
  {
    title: "Редкости и множители",
    text: "Обычный, редкий (зеркала), эпический (пары, последовательности), легендарный (престижные буквы), мифический (тройки и спецномера) и божественный — тройка с престижными буквами в премиальном регионе, от 50 000 000 ₽. Чем выше редкость, тем дороже номер.",
  },
  {
    title: "Ставки",
    text: "Цена прокрутки зависит от редкости: 18 000, 140 000, 560 000, 2 700 000, 6 800 000 и 63 000 000 ₽. Номер может выпасть дешевле или дороже ставки.",
  },
  {
    title: "Энергия",
    text: "Максимум 512, восстанавливается по единице каждые две минуты. Тратится первой, если ты выбрал оплату энергией.",
  },
  {
    title: "Продажа",
    text: "Номер продаётся за свою цену. Купленные за звёзды не продаются. В гараже можно выбрать несколько номеров и продать пачкой.",
  },
  {
    title: "Гараж и слоты",
    text: "Начальный гараж — 22 места. Расширение на 5 мест стоит 200 кристаллов. Доход гаража — 1% стоимости в час.",
  },
  {
    title: "Крафт",
    text: "Выбери 3–7 номеров одной редкости и получи один номер следующей редкости. В половине случаев он дешевле суммы.",
  },
  {
    title: "Сезоны и пропуск",
    text: "Очки сезона дают за прокрутки, задания, охоту и коллекции. Уровни пропуска открывают награды: бесплатные и премиальные.",
  },
  {
    title: "Друзья",
    text: "Приглашай по ссылке, получай награды за ступени и 1% с дорогих номеров друга — не больше 30 000 ₽ в сутки.",
  },
  {
    title: "Рейтинг",
    text: "Место считается по сумме номеров в гараже за сезон или неделю. Продал номер — место падает.",
  },
];

export function SettingsView({
  current,
  refresh,
  notify,
}: {
  current: string;
  refresh: () => Promise<void>;
  notify: (message: string, kind?: "ok" | "err") => void;
}) {
  const [items, setItems] = useState<ThemeItem[]>([]);
  const [active, setActive] = useState(current);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .themes()
      .then((data) => setItems(data.items))
      .catch(() => undefined);
  }, []);

  async function pick(code: string) {
    if (busy) return;
    setBusy(true);
    try {
      await api.setTheme(code);
      document.documentElement.dataset.theme = code;
      setActive(code);
      notify("Тема применена", "ok");
      await refresh();
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="view">
      <div className="section-head">
        <h2>Настройки</h2>
      </div>

      <div className="section-head">
        <h3>Тема</h3>
        <span className="muted small">10 палитр</span>
      </div>

      <div className="theme-grid">
        {items.map((item) => (
          <button
            key={item.code}
            className={active === item.code ? "theme-card theme-card-active" : "theme-card"}
            onClick={() => pick(item.code)}
            disabled={busy}
          >
            <span className="theme-swatches">
              <span className="theme-swatch" style={{ background: item.bg }} />
              <span className="theme-swatch" style={{ background: item.surface }} />
              <span className="theme-swatch" style={{ background: item.accent }} />
            </span>
            <span className="theme-name">{item.title}</span>
          </button>
        ))}
      </div>

      <div className="section-head">
        <h3>Правила игры</h3>
      </div>

      <div className="rules">
        {RULES.map((rule) => (
          <details className="rule" key={rule.title}>
            <summary>{rule.title}</summary>
            <p>{rule.text}</p>
          </details>
        ))}
      </div>
    </section>
  );
}
