export type RarityMeta = { label: string; color: string };

export const RARITY: Record<string, RarityMeta> = {
  common: { label: "Обычный", color: "#9aa0ab" },
  rare: { label: "Редкий", color: "#4da3ff" },
  epic: { label: "Эпический", color: "#b07cff" },
  legendary: { label: "Легендарный", color: "#ffc247" },
  mythic: { label: "Мифический", color: "#ff5c7a" },
};

export const RARITY_ORDER = ["common", "rare", "epic", "legendary", "mythic"];

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
