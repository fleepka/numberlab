import type {
  CollectionT,
  DuelT,
  JoinResult,
  MeResponse,
  Offer,
  PlateT,
  Tx,
} from "./types";

type TelegramWindow = Window & {
  Telegram?: {
    WebApp?: {
      initData: string;
      ready: () => void;
      expand: () => void;
      openInvoice: (url: string, callback?: (status: string) => void) => void;
      HapticFeedback?: { impactOccurred: (style: string) => void };
    };
  };
};

export const tg = (window as TelegramWindow).Telegram?.WebApp;

function devUser(): string | null {
  if (tg?.initData) return null;
  const saved = localStorage.getItem("numberlab.devUser");
  if (saved) return saved;
  const id = String(100000000 + Math.floor(Math.random() * 900000));
  localStorage.setItem("numberlab.devUser", id);
  return id;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init?.headers as Record<string, string>) ?? {}),
  };
  if (tg?.initData) headers["X-Init-Data"] = tg.initData;
  const dev = devUser();
  if (dev) headers["X-Dev-User"] = dev;

  const response = await fetch(path, { ...init, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(typeof body.detail === "string" ? body.detail : "Ошибка запроса");
  }
  return response.json() as Promise<T>;
}

export const api = {
  me: () => request<MeResponse>("/api/me"),
  spin: () =>
    request<{ plate: PlateT; cost: number; coins: number; spin_ready_in: number }>("/api/spin", {
      method: "POST",
    }),
  daily: () =>
    request<{ amount: number; coins: number; streak: number }>("/api/daily", { method: "POST" }),
  garage: () => request<{ plates: PlateT[] }>("/api/garage"),
  sell: (id: number) =>
    request<{ amount: number; coins: number }>(`/api/garage/${id}/sell`, { method: "POST" }),
  history: () => request<{ items: Tx[] }>("/api/history"),
  feed: () =>
    request<{ items: { code: string; rarity: string; score: number; owner: string }[] }>("/api/feed"),
  collections: () => request<{ items: CollectionT[] }>("/api/collections"),
  claimCollection: (id: number) =>
    request<{
      code: string;
      coins: number;
      gems: number;
      xp: number;
      level: number;
      rewards: { coins: number; gems: number; xp: number };
    }>(`/api/collections/${id}/claim`, { method: "POST" }),
  duels: () => request<{ open: DuelT[]; mine: DuelT[] }>("/api/duels"),
  createDuel: (bet: number) =>
    request<{ duel: DuelT; coins: number }>("/api/duels", {
      method: "POST",
      body: JSON.stringify({ bet }),
    }),
  joinDuel: (id: number) => request<JoinResult>(`/api/duels/${id}/join`, { method: "POST" }),
  cancelDuel: (id: number) =>
    request<{ ok: boolean; coins: number }>(`/api/duels/${id}/cancel`, { method: "POST" }),
  shop: () => request<{ offers: Offer[] }>("/api/shop"),
  buy: (code: string) =>
    request<{ dev: boolean; invoice_url: string | null; plate?: PlateT | null }>("/api/shop/buy", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),
};
