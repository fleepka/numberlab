export type RarityMeta = { label: string; color: string };

export const RARITY: Record<string, RarityMeta> = {
  common: { label: "Обычный", color: "#8b93a3" },
  uncommon: { label: "Необычный", color: "#2dd4bf" },
  rare: { label: "Редкий", color: "#38bdf8" },
  epic: { label: "Эпический", color: "#a96bff" },
  legendary: { label: "Легендарный", color: "#ffc44d" },
  mythic: { label: "Мифический", color: "#ff6bd6" },
  unique: { label: "Уникальный", color: "#ff5c7a" },
};

export const RARITY_ORDER = ["common", "uncommon", "rare", "epic", "legendary", "mythic", "unique"];

export function rarityColor(key: string): string {
  return RARITY[key]?.color ?? RARITY.common.color;
}

export function rarityLabel(key: string): string {
  return RARITY[key]?.label ?? key;
}

export function rarityIndex(key: string): number {
  return Math.max(0, RARITY_ORDER.indexOf(key));
}

export function formatCoins(value: number): string {
  return value.toLocaleString("ru-RU");
}

export function formatTime(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) return `${h} ч ${m} мин`;
  if (m > 0) return `${m} мин ${s} с`;
  return `${s} с`;
}
