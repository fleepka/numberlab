import type {
  CollectionT,
  DuelT,
  FriendsData,
  GarageData,
  HuntT,
  JoinResult,
  MeResponse,
  Offer,
  PassData,
  PassReward,
  PlateT,
  RatingData,
  TaskT,
  TicketT,
  Tx,
} from "./types";

type TelegramWindow = Window & {
  Telegram?: {
    WebApp?: {
      initData: string;
      initDataUnsafe?: { start_param?: string };
      ready: () => void;
      expand: () => void;
      openInvoice: (url: string, callback?: (status: string) => void) => void;
      openTelegramLink?: (url: string) => void;
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
  const startParam = tg?.initDataUnsafe?.start_param;
  if (startParam) headers["X-Start-Param"] = startParam;
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
  spin: (tier?: string) =>
    request<{
      plate: PlateT;
      cost: number;
      tier: string;
      coins: number;
      energy: number;
      energy_in: number;
    }>(tier ? `/api/spin?tier=${tier}` : "/api/spin", { method: "POST" }),
  daily: () =>
    request<{ amount: number; coins: number; streak: number }>("/api/daily", { method: "POST" }),
  garage: () => request<GarageData>("/api/garage"),
  sell: (id: number) =>
    request<{ amount: number; coins: number }>(`/api/garage/${id}/sell`, { method: "POST" }),
  sellMany: (ids: number[]) =>
    request<{ amount: number; sold: number; coins: number }>("/api/garage/sell", {
      method: "POST",
      body: JSON.stringify({ ids }),
    }),
  collectIncome: () =>
    request<{ amount: number; coins: number; rate: number }>("/api/garage/income", {
      method: "POST",
    }),
  craft: (ids: number[]) =>
    request<{
      plate: PlateT;
      spent: number;
      value: number;
      target: string;
      target_label: string;
    }>("/api/garage/craft", { method: "POST", body: JSON.stringify({ ids }) }),
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
  tasks: () => request<{ items: TaskT[] }>("/api/tasks"),
  claimTask: (code: string) =>
    request<{
      code: string;
      coins: number;
      gems: number;
      energy: number;
      rewards: { coins: number; energy: number; gems: number };
    }>(`/api/tasks/${code}/claim`, { method: "POST" }),
  rating: (period: "season" | "week" = "season") =>
    request<RatingData>(`/api/rating?period=${period}`),
  friends: () => request<FriendsData>("/api/friends"),
  tickets: () => request<{ items: TicketT[] }>("/api/tickets"),
  hunt: () => request<HuntT>("/api/hunt"),
  claimHunt: () =>
    request<{
      coins: number;
      energy: number;
      rewards: { coins: number; energy: number; ticket: string | null };
    }>("/api/hunt/claim", { method: "POST" }),
  pass: () => request<PassData>("/api/pass"),
  claimPass: (level: number, track: "free" | "premium") =>
    request<{ level: number; track: string; rewards: PassReward }>("/api/pass/claim", {
      method: "POST",
      body: JSON.stringify({ level, track }),
    }),
  buyPass: () =>
    request<{ dev: boolean; premium: boolean; invoice_url: string | null }>("/api/pass/buy", {
      method: "POST",
    }),
  useTicket: (rarity: string) =>
    request<{ plate: PlateT; left: number; coins: number }>("/api/tickets/use", {
      method: "POST",
      body: JSON.stringify({ rarity }),
    }),
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
