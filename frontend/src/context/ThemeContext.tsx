import { createContext, ReactNode, useCallback, useContext, useEffect, useRef, useState } from 'react';
type Theme = 'light' | 'dark';
interface Ctx { theme: Theme; setTheme: (t: Theme) => void; toggleTheme: () => void }
const C = createContext<Ctx>({ theme: 'light', setTheme: () => {}, toggleTheme: () => {} });
export const useTheme = () => useContext(C);
// The initial class is set before first paint by the inline script in _document.tsx (no flash).
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>('light');
  const transitionTimer = useRef<ReturnType<typeof setTimeout>>();
  useEffect(() => { setThemeState(document.documentElement.classList.contains('dark') ? 'dark' : 'light'); }, []);
  const setTheme = useCallback((t: Theme) => {
    document.documentElement.classList.add('theme-transition');
    setThemeState(t);
    document.documentElement.classList.toggle('dark', t === 'dark');
    clearTimeout(transitionTimer.current);
    transitionTimer.current = setTimeout(() => document.documentElement.classList.remove('theme-transition'), 350);
    try { localStorage.setItem('theme', t); } catch {}
  }, []);
  const toggleTheme = useCallback(() => setTheme(document.documentElement.classList.contains('dark') ? 'light' : 'dark'), [setTheme]);
  return <C.Provider value={{ theme, setTheme, toggleTheme }}>{children}</C.Provider>;
}
