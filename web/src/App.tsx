import { useCallback, useEffect, useState } from "react";
import { api, tg } from "./api";
import { CollectionsView } from "./components/Collections";
import { DuelsView } from "./components/Duels";
import { GarageView } from "./components/Garage";
import { ProfileView } from "./components/Profile";
import { ShopView } from "./components/Shop";
import { SpinView } from "./components/Spin";
import type { MeResponse } from "./types";

type Tab = "spin" | "garage" | "collections" | "duels" | "shop" | "profile";

const TABS: { id: Tab; label: string }[] = [
  { id: "spin", label: "Спин" },
  { id: "garage", label: "Гараж" },
  { id: "collections", label: "Коллекции" },
  { id: "duels", label: "Дуэли" },
  { id: "shop", label: "Витрина" },
  { id: "profile", label: "Профиль" },
];

const ICONS: Record<Tab, string> = {
  spin: "M12 3a9 9 0 1 0 9 9M12 7v5l3 2",
  garage: "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z",
  collections: "M12 3l9 5-9 5-9-5 9-5zM3 13l9 5 9-5",
  duels: "M5 19L19 5M14 5h5v5M5 5l5 5M14 14l5 5",
  shop: "M6 8h12l-1 12H7L6 8zM9 8V6a3 3 0 0 1 6 0v2",
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
        <div className="brand">
          NUMBER<span className="brand-accent">LAB</span>
        </div>
        <div className="wallet">
          <div className="coins">
            <span className="coin-icon">М</span>
            {me.user.coins.toLocaleString("ru-RU")}
          </div>
          <div className="gems" title="GEMS">
            <span className="gem-icon">◆</span>
            {me.user.gems}
          </div>
        </div>
      </header>

      <main className="content">
        {tab === "spin" && <SpinView user={me.user} refresh={refresh} notify={notify} />}
        {tab === "garage" && <GarageView refresh={refresh} notify={notify} />}
        {tab === "collections" && <CollectionsView refresh={refresh} notify={notify} />}
        {tab === "duels" && (
          <DuelsView coins={me.user.coins} selfId={me.user.id} refresh={refresh} notify={notify} />
        )}
        {tab === "shop" && <ShopView refresh={refresh} notify={notify} />}
        {tab === "profile" && (
          <ProfileView
            user={me.user}
            garageCount={me.garage_count}
            top={me.top}
            refresh={refresh}
            notify={notify}
          />
        )}
      </main>

      <nav className="nav">
        {TABS.map((item) => (
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
