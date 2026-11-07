import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from 'react';
import * as auth from '@/services/authService';
import type { AuthUser } from '@/services/authService';
interface Ctx { user: AuthUser | null; ready: boolean; login: (e: string, p: string) => Promise<void>; register: (n: string, e: string, p: string) => Promise<void>; logout: () => void; updateUser: (u: AuthUser) => void }
const C = createContext<Ctx>({ user: null, ready: true, login: async () => {}, register: async () => {}, logout: () => {}, updateUser: () => {} });
export const useAuth = () => useContext(C);
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    try { const u = localStorage.getItem('user'); if (localStorage.getItem('token') && u) setUser(JSON.parse(u)); } catch {}
    setReady(true);
  }, []);
  const persist = (r: auth.AuthResult) => { localStorage.setItem('token', r.access_token); localStorage.setItem('user', JSON.stringify(r.user)); setUser(r.user); };
  const login = useCallback(async (e: string, p: string) => persist(await auth.login(e, p)), []);
  const register = useCallback(async (n: string, e: string, p: string) => persist(await auth.register(n, e, p)), []);
  const logout = useCallback(() => { localStorage.removeItem('token'); localStorage.removeItem('user'); setUser(null); }, []);
  const updateUser = useCallback((u: AuthUser) => { localStorage.setItem('user', JSON.stringify(u)); setUser(u); }, []);
  return <C.Provider value={{ user, ready, login, register, logout, updateUser }}>{children}</C.Provider>;
}
