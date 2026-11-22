import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { ChatMessage } from "../types";

export function ChatView({
  selfId,
  notify,
}: {
  selfId: number;
  notify: (message: string, kind?: "ok" | "err") => void;
}) {
  const [items, setItems] = useState<ChatMessage[]>([]);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const lastId = useRef(0);

  async function load(initial = false) {
    try {
      const data = await api.chat(initial ? 0 : lastId.current);
      if (!data.items.length) return;
      lastId.current = data.items[data.items.length - 1].id;
      setItems((prev) => (initial ? data.items : [...prev, ...data.items].slice(-80)));
    } catch (error) {
      if (initial) notify((error as Error).message, "err");
    }
  }

  useEffect(() => {
    void load(true);
    const timer = window.setInterval(() => void load(), 4000);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const value = text.trim();
    if (!value || sending) return;
    setSending(true);
    try {
      await api.sendMessage(value);
      setText("");
      await load();
    } catch (error) {
      notify((error as Error).message, "err");
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="view chat-view">
      <div className="section-head">
        <h2>Общий чат</h2>
        <span className="muted small">без ссылок и спама</span>
      </div>

      <div className="chat-list">
        {items.map((item) => {
          const own = item.user_id === selfId;
          return (
            <div className={own ? "chat-row chat-own" : "chat-row"} key={item.id}>
              <span className="chat-author">{item.username ? `@${item.username}` : item.first_name || "Игрок"}</span>
              <p className="chat-text">{item.text}</p>
            </div>
          );
        })}
        {!items.length && <div className="card muted small">Пока тихо. Напиши первым.</div>}
      </div>

      <form className="chat-form" onSubmit={submit}>
        <input
          className="chat-input"
          value={text}
          maxLength={200}
          placeholder="Сообщение…"
          onChange={(event) => setText(event.target.value)}
        />
        <button className="btn btn-primary btn-sm" type="submit" disabled={sending || !text.trim()}>
          {sending ? "…" : "Отправить"}
        </button>
      </form>
    </section>
  );
}
