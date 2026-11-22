import { useEffect, useState } from "react";
import { api } from "../api";
import { money } from "../format";
import type { AdminMeta, AdminUser } from "../types";

export function AdminView({
  notify,
}: {
  notify: (message: string, kind?: "ok" | "err") => void;
}) {
  const [query, setQuery] = useState("");
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [selected, setSelected] = useState<AdminUser | null>(null);
  const [meta, setMeta] = useState<AdminMeta | null>(null);
  const [amount, setAmount] = useState("1000");
  const [currency, setCurrency] = useState("coins");
  const [rarity, setRarity] = useState("epic");
  const [country, setCountry] = useState("RU");
  const [busy, setBusy] = useState(false);

  async function load(q = query) {
    try {
      setUsers((await api.adminUsers(q)).items);
    } catch (error) {
      notify((error as Error).message, "err");
    }
  }

  useEffect(() => {
    void load("");
    api
      .adminMeta()
      .then(setMeta)
      .catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function open(user: AdminUser) {
    try {
      setSelected(await api.adminUser(user.id));
    } catch (error) {
      notify((error as Error).message, "err");
    }
  }

  async function grant(sign: 1 | -1) {
    if (!selected || busy) return;
    const value = Math.round(Number(amount));
    if (!Number.isFinite(value) || value <= 0) {
      notify("Введите сумму", "err");
      return;
    }
    setBusy(true);
    try {
      await api.adminGrant(selected.id, currency, sign * value);
      notify(`${sign > 0 ? "Начислено" : "Списано"} ${value} (${currency})`, "ok");
      await open(selected);
      await load();
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setBusy(false);
    }
  }

  async function givePlate() {
    if (!selected || busy) return;
    setBusy(true);
    try {
      const result = await api.adminPlate(selected.id, rarity, country);
      notify(`Выдан ${result.plate.code}`, "ok");
      await open(selected);
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setBusy(false);
    }
  }

  async function toggleBan() {
    if (!selected || busy) return;
    setBusy(true);
    try {
      const result = await api.adminBan(selected.id, !selected.is_banned);
      notify(result.is_banned ? "Заблокирован" : "Разблокирован", "ok");
      await open(selected);
      await load();
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setBusy(false);
    }
  }

  async function cleanup() {
    if (busy) return;
    setBusy(true);
    try {
      const result = await api.adminCleanup();
      notify(`Удалено старых номеров: ${result.removed}`, "ok");
      await load();
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="view">
      <div className="section-head">
        <h2>Админка</h2>
        <span className="muted small">{users.length} игроков</span>
      </div>

      <form
        className="chat-form"
        onSubmit={(event) => {
          event.preventDefault();
          void load();
        }}
      >
        <input
          className="chat-input"
          value={query}
          placeholder="ID, ник или @username"
          onChange={(event) => setQuery(event.target.value)}
        />
        <button className="btn btn-primary btn-sm" type="submit">
          Найти
        </button>
      </form>

      <div className="task-list">
        {users.map((user) => (
          <button
            className={selected?.id === user.id ? "card rating-row rating-self" : "card rating-row"}
            key={user.id}
            onClick={() => open(user)}
            style={{ width: "100%", textAlign: "left" }}
          >
            <div className="rating-name">
              <div>
                {user.name} {user.username ? `@${user.username}` : ""}
              </div>
              <div className="muted small">
                id {user.id} · tg {user.tg_id} · ур. {user.level}
                {user.is_banned ? " · забанен" : ""}
              </div>
            </div>
            <span className="price">{money(user.coins)}</span>
          </button>
        ))}
      </div>

      {selected && (
        <div className="card">
          <div className="section-head">
            <h3>{selected.name}</h3>
            <span className="muted small">id {selected.id}</span>
          </div>

          <div className="stat-grid">
            <div className="stat">
              <span className="stat-value">{money(selected.coins)}</span>
              <span className="stat-label">рубли</span>
            </div>
            <div className="stat">
              <span className="stat-value stat-gems">{selected.gems} ◆</span>
              <span className="stat-label">кристаллы</span>
            </div>
            <div className="stat">
              <span className="stat-value">⚡{selected.energy}</span>
              <span className="stat-label">энергия</span>
            </div>
          </div>

          <div className="muted small">
            гараж: {selected.garage_count ?? 0} шт · {money(selected.garage_value ?? 0)} · мест{" "}
            {selected.garage_slots} · спинов {selected.spins}
          </div>

          <div className="chips">
            {["coins", "gems", "energy"].map((item) => (
              <button
                key={item}
                className={currency === item ? "chip chip-active" : "chip"}
                onClick={() => setCurrency(item)}
              >
                {item === "coins" ? "₽" : item === "gems" ? "◆" : "⚡"}
              </button>
            ))}
          </div>

          <div className="chips">
            <input
              className="chat-input bid-input"
              value={amount}
              inputMode="numeric"
              onChange={(event) => setAmount(event.target.value)}
            />
            <button className="btn btn-primary btn-sm" onClick={() => grant(1)} disabled={busy}>
              Начислить
            </button>
            <button className="btn btn-ghost btn-sm" onClick={() => grant(-1)} disabled={busy}>
              Списать
            </button>
          </div>

          <div className="chips">
            {(meta?.rarities ?? []).map((item) => (
              <button
                key={item.code}
                className={rarity === item.code ? "chip chip-active" : "chip"}
                onClick={() => setRarity(item.code)}
              >
                {item.label}
              </button>
            ))}
          </div>
          <div className="chips">
            {(meta?.countries ?? []).map((item) => (
              <button
                key={item.code}
                className={country === item.code ? "chip chip-active" : "chip"}
                onClick={() => setCountry(item.code)}
              >
                {item.flag}
              </button>
            ))}
          </div>
          <button className="btn btn-gold btn-sm" onClick={givePlate} disabled={busy}>
            Выдать номер
          </button>

          <button className="btn btn-ghost btn-sm" onClick={toggleBan} disabled={busy}>
            {selected.is_banned ? "Разблокировать" : "Заблокировать"}
          </button>
        </div>
      )}

      <button className="btn btn-ghost btn-sm" onClick={cleanup} disabled={busy}>
        Удалить старые редкости
      </button>
    </section>
  );
}
