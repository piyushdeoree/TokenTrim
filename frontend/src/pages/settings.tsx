import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Select } from '@/components/ui/Select';
import { useToast } from '@/components/ui/Toast';
import { useTheme } from '@/context/ThemeContext';
import { useAuth } from '@/context/AuthContext';
import { useModelPricing } from '@/hooks/useModelPricing';
export default function Settings() {
  const { theme, setTheme } = useTheme(); const { user, logout } = useAuth(); const toast = useToast(); const { state } = useModelPricing();
  const [model, setModel] = useState(''); const [notify, setNotify] = useState(true);
  useEffect(() => { try { const s = JSON.parse(localStorage.getItem('settings') ?? '{}'); setModel(s.model ?? ''); setNotify(s.notify ?? true); } catch {} }, []);
  const save = () => { try { localStorage.setItem('settings', JSON.stringify({ model, notify })); toast('Settings saved.'); } catch { toast('Unable to save settings.'); } }; // TODO: persist to backend when endpoint exists
  return (
    <main className="mx-auto max-w-2xl space-y-4 p-4 lg:p-8">
      <h1 className="text-xl font-semibold">Settings</h1>
      <Card title="Preferences"><div className="space-y-3 text-sm">
        <Select label="Default model" value={model} onChange={(e) => setModel(e.target.value)}>
          <option value="">No default</option>{state.status === 'success' && state.data.map((m) => <option key={m.model}>{m.model}</option>)}</Select>
        <Select label="Theme" value={theme} onChange={(e) => setTheme(e.target.value as 'light' | 'dark')}><option value="light">Light</option><option value="dark">Dark</option></Select>
        <label className="flex items-center gap-2"><input type="checkbox" checked={notify} onChange={(e) => setNotify(e.target.checked)} /> Email me when a key nears its usage limit</label>
        <Button onClick={save}>Save settings</Button></div></Card>
      <Card title="Account"><p className="mb-3 text-sm">Signed in as {user?.email}</p><Button variant="ghost" onClick={logout}>Sign out</Button></Card>
      <Card title="Billing"><p className="text-sm">Billing is informational in this project. No payment integration.</p></Card>
    </main>
  );
}
