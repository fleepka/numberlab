import { useCallback, useEffect, useState } from "react";
import { api, tg } from "./api";
import { ChatView } from "./components/Chat";
import { CollectionsView } from "./components/Collections";
import { DuelsView } from "./components/Duels";
import { FriendsView } from "./components/Friends";
import { GarageView } from "./components/Garage";
import { PassView } from "./components/Pass";
import { ProfileView } from "./components/Profile";
import { RatingView } from "./components/Rating";
import { ShopView } from "./components/Shop";
import { SpinView } from "./components/Spin";
import { TasksView } from "./components/Tasks";
import { TicketsView } from "./components/Tickets";
import { shortMoney } from "./format";
import type { MeResponse } from "./types";

type Tab =
  | "spin"
  | "garage"
  | "collections"
  | "duels"
  | "shop"
  | "tasks"
  | "rating"
  | "friends"
  | "tickets"
  | "pass"
  | "chat"
  | "profile";

const NAV: { id: Tab; label: string }[] = [
  { id: "spin", label: "Главная" },
  { id: "garage", label: "Гараж" },
  { id: "rating", label: "Рейтинг" },
  { id: "tasks", label: "Задания" },
  { id: "friends", label: "Друзья" },
];

export type TabId = Tab;

const ICONS: Record<Tab, string> = {
  spin: "M12 3a9 9 0 1 0 9 9M12 7v5l3 2",
  garage: "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z",
  collections: "M12 3l9 5-9 5-9-5 9-5zM3 13l9 5 9-5",
  duels: "M5 19L19 5M14 5h5v5M5 5l5 5M14 14l5 5",
  shop: "M6 8h12l-1 12H7L6 8zM9 8V6a3 3 0 0 1 6 0v2",
  tasks: "M8 6h11M8 12h11M8 18h11M4 6l1 1 2-2M4 12l1 1 2-2M4 18l1 1 2-2",
  rating: "M8 21V10M12 21V4M16 21v-7M4 21h16",
  friends: "M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM2 20a7 7 0 0 1 14 0M17 12a3 3 0 1 0 0-6M18 20a6 6 0 0 0-2-4.5",
  tickets: "M4 8a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2 2 2 0 0 0 0 4 2 2 0 0 1-2 2H6a2 2 0 0 1-2-2 2 2 0 0 0 0-4zM9 6v8",
  pass: "M5 4h14v16H5zM9 9h6M9 13h6M9 17h3",
  chat: "M4 6h16v10H9l-5 4V6z",
  profile: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21a8 8 0 0 1 16 0",
};

function Icon({ name }: { name: Tab }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={ICONS[name]} />
    </svg>
  );
}

export default function App() {
  const [tab, setTab] = useState<Tab>("spin");
  const [me, setMe] = useState<MeResponse | null>(null);
  const [fatal, setFatal] = useState<string | null>(null);
  const [toast, setToast] = useState<{ text: string; kind: "ok" | "err" } | null>(null);

  const refresh = useCallback(async () => {
    setMe(await api.me());
  }, []);

  useEffect(() => {
    tg?.ready();
    tg?.expand();
    refresh().catch((error: Error) => setFatal(error.message));
  }, [refresh]);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 2600);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const notify = useCallback((text: string, kind: "ok" | "err" = "ok") => {
    setToast({ text, kind });
  }, []);

  if (fatal) {
    return (
      <div className="boot">
        <div className="panel">
          <h2>Не удалось подключиться</h2>
          <p className="muted">{fatal}</p>
        </div>
      </div>
    );
  }

  if (!me) {
    return (
      <div className="boot">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="app">
      <header className="topbar">
        <button className="avatar" onClick={() => setTab("profile")}>
          {me.user.photo_url ? (
            <img src={me.user.photo_url} alt="" />
          ) : (
            <span>{(me.user.first_name || "И").slice(0, 1).toUpperCase()}</span>
          )}
          <span className="avatar-level">{me.user.level}</span>
        </button>

        <div className="profile-meta">
          <div className="profile-name">{me.user.first_name || "Игрок"}</div>
          <div className="xp-line">
            <div
              className="xp-fill"
              style={{ width: `${Math.min(100, Math.round(((400 - me.user.xp_to_next) / 400) * 100))}%` }}
            />
          </div>
        </div>

        <div className="pills">
          <div className="pill" title="Энергия">
            ⚡ {me.user.energy}
          </div>
          <div className="pill pill-coins" title="Баланс">
            {shortMoney(me.user.coins)}
          </div>
          <button className="pill pill-gift" title="Магазин" onClick={() => setTab("shop")}>
            🎁
          </button>
        </div>
      </header>

      <main className="content">
        {tab === "spin" && (
          <SpinView
            user={me.user}
            stakes={me.stakes}
            energyCosts={me.energy_costs}
            refresh={refresh}
            notify={notify}
            onNavigate={(next) => setTab(next)}
          />
        )}
        {tab === "garage" && <GarageView refresh={refresh} notify={notify} />}
        {tab === "collections" && <CollectionsView refresh={refresh} notify={notify} />}
        {tab === "duels" && (
          <DuelsView coins={me.user.coins} selfId={me.user.id} refresh={refresh} notify={notify} />
        )}
        {tab === "shop" && <ShopView refresh={refresh} notify={notify} />}
        {tab === "tasks" && <TasksView user={me.user} refresh={refresh} notify={notify} />}
        {tab === "tickets" && <TicketsView refresh={refresh} notify={notify} />}
        {tab === "pass" && <PassView refresh={refresh} notify={notify} />}
        {tab === "chat" && <ChatView selfId={me.user.id} notify={notify} />}
        {tab === "rating" && <RatingView selfId={me.user.id} notify={notify} />}
        {tab === "friends" && <FriendsView selfId={me.user.id} notify={notify} />}
        {tab === "profile" && (
          <ProfileView
            user={me.user}
            garageCount={me.garage_count}
            top={me.top}
            refresh={refresh}
            notify={notify}
            onNavigate={(next) => setTab(next)}
          />
        )}
      </main>

      <nav className="nav">
        {NAV.map((item) => (
          <button
            key={item.id}
            className={tab === item.id ? "nav-item nav-active" : "nav-item"}
            onClick={() => setTab(item.id)}
          >
            <Icon name={item.id} />
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      {toast && <div className={`toast toast-${toast.kind}`}>{toast.text}</div>}
    </div>
  );
}
