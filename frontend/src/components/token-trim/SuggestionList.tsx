export function SuggestionList({ items }: { items: string[] }) {
  if (!items.length) return <p className="text-sm text-slate-600">No suggestions.</p>;
  return <ul className="list-disc space-y-1 pl-5 text-sm">{items.map((s, i) => <li key={i}>{s}</li>)}</ul>;
}
