import { createContext, ReactNode, useCallback, useContext, useState } from 'react';
const C = createContext<(m: string) => void>(() => {});
export const useToast = () => useContext(C);
export function ToastProvider({ children }: { children: ReactNode }) {
  const [msgs, setMsgs] = useState<{ id: number; text: string }[]>([]);
  const push = useCallback((text: string) => {
    const id = Date.now() + Math.random(); setMsgs((m) => [...m, { id, text }]);
    setTimeout(() => setMsgs((m) => m.filter((x) => x.id !== id)), 3500);
  }, []);
  return (<C.Provider value={push}>{children}
    <div role="status" aria-live="polite" className="fixed bottom-4 right-4 z-50 space-y-2">
      {msgs.map((m) => <div key={m.id} className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white shadow dark:bg-slate-100 dark:text-slate-900">{m.text}</div>)}
    </div></C.Provider>);
}
