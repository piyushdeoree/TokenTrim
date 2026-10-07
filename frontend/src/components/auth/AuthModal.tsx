import { useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Field } from '@/components/ui/Field';
import { useAuth } from '@/context/AuthContext';
export type AuthMode = 'login' | 'register';
export function AuthModal({ mode, onModeChange, onClose, onSuccess }: { mode: AuthMode; onModeChange: (m: AuthMode) => void; onClose: () => void; onSuccess: () => void }) {
  const { login, register } = useAuth();
  const [f, setF] = useState({ name: '', email: '', password: '' });
  const [err, setErr] = useState(''); const [busy, setBusy] = useState(false);
  const isLogin = mode === 'login';
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isLogin && !f.name.trim()) return setErr('Enter your name.');
    if (!/^\S+@\S+\.\S+$/.test(f.email)) return setErr('Enter a valid email address.');
    if (isLogin ? !f.password : f.password.length < 8) return setErr(isLogin ? 'Enter your password.' : 'Password must be at least 8 characters.');
    setBusy(true); setErr('');
    try { isLogin ? await login(f.email, f.password) : await register(f.name, f.email, f.password); onSuccess(); }
    catch { setErr(isLogin ? 'Sign in failed. Check your email and password.' : 'Unable to create account. Please try again.'); }
    finally { setBusy(false); }
  };
  return (
    <Modal title={isLogin ? 'Sign in to TokenTrim' : 'Create your account'} onClose={onClose}>
      <form onSubmit={submit} noValidate className="space-y-3">
        {!isLogin && <Field label="Name" autoComplete="name" value={f.name} onChange={set('name')} />}
        <Field label="Email" type="email" autoComplete="email" value={f.email} onChange={set('email')} />
        <Field label="Password" type="password" autoComplete={isLogin ? 'current-password' : 'new-password'} value={f.password} onChange={set('password')} />
        {err && <p role="alert" className="text-sm text-red-700 dark:text-red-400">{err}</p>}
        <Button type="submit" className="w-full" loading={busy}>{isLogin ? 'Sign in' : 'Create account'}</Button>
      </form>
      <p className="mt-3 text-sm">{isLogin ? 'No account? ' : 'Have an account? '}
        <button type="button" className="underline" onClick={() => { setErr(''); onModeChange(isLogin ? 'register' : 'login'); }}>{isLogin ? 'Create one' : 'Sign in'}</button></p>
    </Modal>
  );
}
