import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from 'react';
type Theme = 'light' | 'dark';
interface Ctx { theme: Theme; setTheme: (t: Theme) => void; toggleTheme: () => void }
const C = createContext<Ctx>({ theme: 'light', setTheme: () => {}, toggleTheme: () => {} });
export const useTheme = () => useContext(C);
// The initial class is set before first paint by the inline script in _document.tsx (no flash).
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>('light');
  useEffect(() => { setThemeState(document.documentElement.classList.contains('dark') ? 'dark' : 'light'); }, []);
  const setTheme = useCallback((t: Theme) => {
    setThemeState(t);
    document.documentElement.classList.toggle('dark', t === 'dark');
    try { localStorage.setItem('theme', t); } catch {}
  }, []);
  const toggleTheme = useCallback(() => setTheme(document.documentElement.classList.contains('dark') ? 'light' : 'dark'), [setTheme]);
  return <C.Provider value={{ theme, setTheme, toggleTheme }}>{children}</C.Provider>;
}
