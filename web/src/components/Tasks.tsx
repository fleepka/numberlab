import { useEffect, useState } from "react";
import { api } from "../api";
import { money } from "../format";
import type { TaskT, UserT } from "../types";

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
  const [kind, setKind] = useState<Kind>("daily");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const data = await api.tasks();
      setItems(data.items);
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
