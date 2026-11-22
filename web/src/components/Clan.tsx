import { useEffect, useState } from "react";
import { api } from "../api";
import { money } from "../format";
import type { ClanT } from "../types";

export function ClanView({
  refresh,
  notify,
}: {
  refresh: () => Promise<void>;
  notify: (message: string, kind?: "ok" | "err") => void;
}) {
  const [clan, setClan] = useState<ClanT | null>(null);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      const data = await api.clan();
      setClan(data.clan);
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

  async function create() {
    if (busy) return;
    setBusy("create");
    try {
      const data = await api.createClan(name.trim());
      setClan(data.clan);
      setName("");
      notify("Клан создан", "ok");
      await refresh();
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setBusy(null);
    }
  }

  async function join() {
    if (busy) return;
    setBusy("join");
    try {
      const data = await api.joinClan(code.trim());
      setClan(data.clan);
      setCode("");
      notify("Ты в клане", "ok");
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setBusy(null);
    }
  }

  async function leave() {
    if (busy) return;
    setBusy("leave");
    try {
      const data = await api.leaveClan();
      setClan(data.clan);
      notify("Ты вышел из клана", "ok");
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setBusy(null);
    }
  }

  if (loading) return <div className="view center muted">Загружаем клан…</div>;

  return (
    <section className="view">
      <div className="section-head">
        <h2>Клан</h2>
        <span className="muted small">{clan ? `${clan.members.length} / ${clan.max}` : "30 мест"}</span>
      </div>

      {clan ? (
        <>
          <div className="card clan-card">
            <div className="clan-head">
              <div>
                <div className="hunt-label">Клан</div>
                <div className="clan-title">{clan.name}</div>
              </div>
              <span className="badge">код {clan.code}</span>
            </div>
            <div className="clan-stats">
              <div className="clan-stat">
                <span className="clan-value">{money(clan.total)}</span>
                <span className="muted small">стоимость</span>
              </div>
              <div className="clan-stat">
                <span className="clan-value">{clan.members.length}</span>
                <span className="muted small">участников</span>
              </div>
            </div>
            <p className="muted small">Скинь код другу — он вступит и добавит номера в общую копилку.</p>
            <button className="btn btn-ghost" onClick={leave} disabled={busy !== null}>
              {busy === "leave" ? "…" : "Выйти из клана"}
            </button>
          </div>

          <div className="card">
            <div className="section-head">
              <h3>Участники</h3>
            </div>
            <div className="list">
              {clan.members.map((member) => (
                <div className="row" key={member.user_id}>
                  <div>
                    <div className="row-title">
                      {member.name}
                      {member.owner && <span className="badge">лидер</span>}
                    </div>
                    <div className="muted small">LVL {member.level}</div>
                  </div>
                  <span className="price">{money(member.value)}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      ) : (
        <>
          <div className="card">
            <div className="section-head">
              <h3>Создать клан</h3>
              <span className="price">{money(5000)}</span>
            </div>
            <p className="muted small">
              Общая копилка номеров, место в клановом рейтинге и 30 мест для друзей.
            </p>
            <input
              value={name}
              maxLength={20}
              placeholder="Название клана"
              onChange={(event) => setName(event.target.value)}
            />
            <button
              className="btn btn-primary"
              onClick={create}
              disabled={busy !== null || name.trim().length < 3}
            >
              {busy === "create" ? "…" : "Создать · 5 000 ₽"}
            </button>
          </div>

          <div className="card">
            <div className="section-head">
              <h3>Вступить по коду</h3>
            </div>
            <input
              value={code}
              maxLength={8}
              placeholder="Например, A1B2C3"
              onChange={(event) => setCode(event.target.value.toUpperCase())}
            />
            <button
              className="btn btn-ghost"
              onClick={join}
              disabled={busy !== null || code.trim().length < 4}
            >
              {busy === "join" ? "…" : "Вступить"}
            </button>
          </div>
        </>
      )}
    </section>
  );
}
