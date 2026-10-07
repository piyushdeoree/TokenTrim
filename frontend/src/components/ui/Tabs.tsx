import { ReactNode, useState } from 'react';
export function Tabs({ tabs }: { tabs: { id: string; label: string; content: ReactNode }[] }) {
  const [active, setActive] = useState(tabs[0].id);
  const onKey = (e: React.KeyboardEvent, i: number) => {
    if (e.key === 'ArrowRight') setActive(tabs[(i + 1) % tabs.length].id);
    if (e.key === 'ArrowLeft') setActive(tabs[(i - 1 + tabs.length) % tabs.length].id);
  };
  return (
    <div>
      <div role="tablist" className="mb-4 flex gap-2 border-b border-slate-200 dark:border-slate-700">
        {tabs.map((t, i) => (
          <button key={t.id} role="tab" id={`tab-${t.id}`} aria-selected={active === t.id} aria-controls={`panel-${t.id}`} tabIndex={active === t.id ? 0 : -1}
            onClick={() => setActive(t.id)} onKeyDown={(e) => onKey(e, i)}
            className={`px-3 py-2 text-sm font-medium ${active === t.id ? 'border-b-2 border-teal-700 text-teal-800 dark:text-teal-300' : 'text-slate-600 dark:text-slate-400'}`}>{t.label}</button>
        ))}
      </div>
      {tabs.map((t) => active === t.id && <div key={t.id} role="tabpanel" id={`panel-${t.id}`} aria-labelledby={`tab-${t.id}`}>{t.content}</div>)}
    </div>
  );
}
