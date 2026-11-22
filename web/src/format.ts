export function money(value: number): string {
  return `${value.toLocaleString("ru-RU")} ₽`;
}

export function shortMoney(value: number): string {
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1).replace(".", ",")} млн ₽`;
  }
  if (value >= 100_000) {
    return `${Math.round(value / 1000)} тыс ₽`;
  }
  return money(value);
}

export function daysLeftInMonth(today: Date = new Date()): number {
  const last = new Date(today.getFullYear(), today.getMonth() + 1, 0);
  return last.getDate() - today.getDate();
}
