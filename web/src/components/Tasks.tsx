import { useEffect, useState } from "react";
import { api } from "../api";
import type { TaskT } from "../types";

const GROUPS: { kind: string; title: string }[] = [
  { kind: "daily", title: "Ежедневные" },
  { kind: "weekly", title: "Еженедельные" },
  { kind: "once", title: "Разовые" },
];

export function TasksView({
  refresh,
  notify,
}: {
  refresh: () => Promise<void>;
  notify: (message: string, kind?: "ok" | "err") => void;
}) {
  const [items, setItems] = useState<TaskT[]>([]);
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
      if (result.rewards.coins) parts.push(`+${result.rewards.coins} монет`);
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

  return (
    <section className="view">
      {GROUPS.map((group) => {
        const tasks = items.filter((item) => item.kind === group.kind);
        if (!tasks.length) return null;
        const ready = tasks.filter((item) => item.done && !item.claimed).length;

        return (
          <div className="task-group" key={group.kind}>
            <div className="section-head">
              <h2>{group.title}</h2>
              <span className="muted">
                {ready > 0 ? `${ready} к получению` : `${tasks.length} заданий`}
              </span>
            </div>

            <div className="task-list">
              {tasks.map((task) => {
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
            </div>
          </div>
        );
      })}
    </section>
  );
}
