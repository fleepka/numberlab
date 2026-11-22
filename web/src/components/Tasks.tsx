import { useEffect, useState } from "react";
import { api } from "../api";
import { money } from "../format";
import type { HuntT, NickT, TaskT, UserT } from "../types";

type Kind = "daily" | "weekly" | "once";

const SEGMENTS: { kind: Kind; label: string }[] = [
  { kind: "daily", label: "Ежедневные" },
  { kind: "weekly", label: "Еженедельные" },
  { kind: "once", label: "Разовые" },
];

function plural(value: number, one: string, few: string, many: string): string {
  const mod10 = value % 10;
  const mod100 = value % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;
  return many;
}

function StreakStrip({ streak }: { streak: number }) {
  const filled = Math.min(streak, 7);
  return (
    <div className="card streak-card">
      <div className="streak-head">
        <div>
          <div className="streak-title">
            {streak} {plural(streak, "день", "дня", "дней")} подряд
          </div>
          <div className="muted small">Заходи каждый день и забирай бонус</div>
        </div>
      </div>
      <div className="streak-row">
        {Array.from({ length: 7 }, (_, index) => {
          const day = index + 1;
          const done = day <= filled;
          const next = day === filled + 1;
          return (
            <div
              className={
                done ? "streak-cell streak-done" : next ? "streak-cell streak-next" : "streak-cell"
              }
              key={day}
            >
              <span className="streak-day">{day}</span>
              <span className="streak-mark">{done ? "✓" : next ? "Бонус" : "—"}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function TasksView({
  user,
  refresh,
  notify,
}: {
  user: UserT;
  refresh: () => Promise<void>;
  notify: (message: string, kind?: "ok" | "err") => void;
}) {
  const [items, setItems] = useState<TaskT[]>([]);
  const [hunt, setHunt] = useState<HuntT | null>(null);
  const [nick, setNick] = useState<NickT | null>(null);
  const [kind, setKind] = useState<Kind>("daily");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const [tasks, daily, nickState] = await Promise.all([api.tasks(), api.hunt(), api.nick()]);
      setItems(tasks.items);
      setHunt(daily);
      setNick(nickState);
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

  async function claim(task: TaskT) {
    if (busy !== null) return;
    setBusy(task.code);
    try {
      const result = await api.claimTask(task.code);
      const parts: string[] = [];
      if (result.rewards.coins) parts.push(`+${money(result.rewards.coins)}`);
      if (result.rewards.energy) parts.push(`+${result.rewards.energy} энергии`);
      if (result.rewards.gems) parts.push(`+${result.rewards.gems} GEMS`);
      notify(`${task.title}: ${parts.join(", ") || "награда получена"}`, "ok");
      await Promise.all([load(), refresh()]);
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setBusy(null);
    }
  }

  async function claimHunt() {
    if (busy !== null) return;
    setBusy("hunt");
    try {
      const result = await api.claimHunt();
      const parts = [`+${money(result.rewards.coins)}`];
      if (result.rewards.energy) parts.push(`+${result.rewards.energy} энергии`);
      if (result.rewards.ticket) parts.push("+ билет");
      notify(`Охота дня: ${parts.join(", ")}`, "ok");
      await Promise.all([load(), refresh()]);
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setBusy(null);
    }
  }

  async function claimNick(days: 7 | 14) {
    if (busy !== null) return;
    setBusy(`nick${days}`);
    try {
      const result = await api.claimNick(days);
      notify(`Ник: билет «${result.ticket}» получен`, "ok");
      await Promise.all([load(), refresh()]);
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setBusy(null);
    }
  }

  if (loading) return <div className="view center muted">Загружаем задания…</div>;

  const visible = items.filter((item) => item.kind === kind);
  const ready = visible.filter((item) => item.done && !item.claimed).length;

  return (
    <section className="view">
      <div className="section-head">
        <h2>Задания</h2>
        <span className="muted small">
          {ready > 0 ? `${ready} к получению` : `${visible.length} заданий`}
        </span>
      </div>

      <StreakStrip streak={user.streak} />

      {hunt && (
        <div className={hunt.claimed ? "card hunt-card claimed" : "card hunt-card"}>
          <div className="hunt-head">
            <div>
              <div className="hunt-label">Охота дня</div>
              <div className="hunt-title">{hunt.title}</div>
            </div>
            <div className="hunt-reward">
              <span className="price">{money(hunt.reward_coins)}</span>
              {hunt.reward_energy > 0 && <span className="energy-text">⚡{hunt.reward_energy}</span>}
              {hunt.reward_ticket && <span className="gems-text">билет</span>}
            </div>
          </div>
          <div className="hunt-foot">
            <span className={hunt.done ? "hunt-state hunt-state-done" : "hunt-state"}>
              {hunt.claimed ? "награда получена" : hunt.done ? "выполнено — забирай" : "крути, пока не выпадет"}
            </span>
            <button
              className="btn btn-primary btn-sm"
              onClick={claimHunt}
              disabled={!hunt.done || hunt.claimed || busy !== null}
            >
              {busy === "hunt" ? "…" : "Забрать"}
            </button>
          </div>
        </div>
      )}

      {nick && (
        <div className="card nick-card">
          <div className="hunt-label">Дополнительное задание</div>
          <div className="hunt-title">Поставь @NumbersLab_off в ник</div>
          <p className="muted small">
            Держи его в имени Telegram: за 7 дней — мифический билет, за 14 — легендарный.
          </p>
          <div className="nick-status">
            {nick.holding ? `Держишь ${nick.days} дн.` : "Тег в имени не найден"}
          </div>
          <div className="nick-actions">
            <button
              className="btn btn-ghost btn-sm"
              disabled={!nick.holding || nick.days < 7 || nick.claimed7 || busy !== null}
              onClick={() => claimNick(7)}
            >
              {nick.claimed7 ? "7 дней ✓" : busy === "nick7" ? "…" : "7 дней · мифический"}
            </button>
            <button
              className="btn btn-ghost btn-sm"
              disabled={!nick.holding || nick.days < 14 || nick.claimed14 || busy !== null}
              onClick={() => claimNick(14)}
            >
              {nick.claimed14 ? "14 дней ✓" : busy === "nick14" ? "…" : "14 дней · легендарный"}
            </button>
          </div>
        </div>
      )}

      <div className="segmented">
        {SEGMENTS.map((segment) => (
          <button
            key={segment.kind}
            className={kind === segment.kind ? "segment segment-active" : "segment"}
            onClick={() => setKind(segment.kind)}
          >
            {segment.label}
          </button>
        ))}
      </div>

      <div className="task-list">
        {visible.map((task) => {
          const percent = Math.min(100, Math.round((task.progress / task.target) * 100));
          return (
            <article className={task.claimed ? "card task-card claimed" : "card task-card"} key={task.code}>
              <div className="task-head">
                <div>
                  <div className="task-title">{task.title}</div>
                  <div className="muted small">{task.description}</div>
                </div>
                <div className="task-rewards">
                  {task.reward_energy > 0 && <span className="energy-text">⚡{task.reward_energy}</span>}
                  {task.reward_coins > 0 && <span className="price">{task.reward_coins} М</span>}
                  {task.reward_gems > 0 && <span className="gems-text">◆{task.reward_gems}</span>}
                </div>
              </div>

              <div className="progress">
                <div
                  className={task.done ? "progress-fill progress-done" : "progress-fill"}
                  style={{ width: `${percent}%` }}
                />
              </div>

              <div className="collection-foot">
                <span className="muted small">
                  {task.progress} / {task.target}
                </span>
                {task.claimed ? (
                  <span className="badge">получено</span>
                ) : (
                  <button
                    className="btn btn-primary btn-sm"
                    disabled={!task.done || busy === task.code}
                    onClick={() => claim(task)}
                  >
                    {busy === task.code ? "…" : "Забрать"}
                  </button>
                )}
              </div>
            </article>
          );
        })}
        {!visible.length && <div className="card muted small">Здесь пока пусто</div>}
      </div>
    </section>
  );
}
