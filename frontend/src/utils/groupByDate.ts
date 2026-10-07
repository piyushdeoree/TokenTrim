export function groupByDate<T extends { date: string }>(items: T[], now = new Date()) {
  const order = ['Today', 'Yesterday', 'Previous 7 days', 'Older'];
  const g: Record<string, T[]> = {};
  const today = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
  for (const it of [...items].sort((a, b) => b.date.localeCompare(a.date))) {
    const [y, m, d] = it.date.split('-').map(Number);
    const diff = Math.round((today - Date.UTC(y, m - 1, d)) / 864e5);
    const k = diff <= 0 ? 'Today' : diff === 1 ? 'Yesterday' : diff <= 7 ? 'Previous 7 days' : 'Older';
    (g[k] ??= []).push(it);
  }
  return order.filter((k) => g[k]).map((k) => ({ label: k, items: g[k] }));
}
