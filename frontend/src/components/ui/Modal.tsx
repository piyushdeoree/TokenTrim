import { ReactNode, useEffect, useRef } from 'react';
export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const closeRef = useRef(onClose); closeRef.current = onClose;
  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    const box = ref.current!;
    (box.querySelector<HTMLElement>('input,select,textarea') ?? box.querySelector<HTMLElement>('button'))?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') return closeRef.current();
      if (e.key !== 'Tab') return;
      const f = Array.from(box.querySelectorAll<HTMLElement>('input,select,textarea,button,a[href]')).filter((x) => !x.hasAttribute('disabled'));
      if (!f.length) return;
      const first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    document.addEventListener('keydown', onKey);
    return () => { document.removeEventListener('keydown', onKey); prev?.focus(); };
  }, []);
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div ref={ref} role="dialog" aria-modal="true" aria-label={title} className="relative max-h-[90vh] w-full max-w-md overflow-auto rounded-xl border border-black/10 bg-card p-6 shadow-xl dark:border-white/10">
        <h2 className="mb-4 pr-8 text-lg font-semibold">{title}</h2>
        {children}
        <button type="button" aria-label="Close dialog" onClick={onClose} className="absolute right-3 top-3 rounded-md px-2 py-1 text-lg leading-none hover:bg-black/10 dark:hover:bg-white/10">×</button>
      </div>
    </div>
  );
}
