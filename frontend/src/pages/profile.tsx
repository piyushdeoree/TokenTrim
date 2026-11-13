import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Field } from '@/components/ui/Field';
import { useToast } from '@/components/ui/Toast';
import { useAuth } from '@/context/AuthContext';
import { apiClient } from '@/services/apiClient';
import { toMessage } from '@/services/apiClient';
export default function Profile() {
  const { user, updateUser } = useAuth(); const toast = useToast();
  const [name, setName] = useState(user?.name ?? ''); const [email, setEmail] = useState(user?.email ?? '');
  const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  useEffect(() => { apiClient.get('/auth/me').then(({ data }) => { setName(data.full_name); setEmail(data.email); updateUser({ name: data.full_name, email: data.email }); }).catch((e) => setError(toMessage(e))); }, [updateUser]);
  const save = async () => {
    setBusy(true); setError('');
    try { const { data } = await apiClient.patch('/auth/me', { full_name: name.trim() }); updateUser({ name: data.full_name, email: data.email }); toast('Profile saved.'); }
    catch (e) { setError(toMessage(e)); } finally { setBusy(false); }
  };
  return (
    <main className="mx-auto max-w-2xl p-4 lg:p-8">
      <h1 className="mb-4 text-xl font-semibold">Profile</h1>
      <Card><div className="space-y-3">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <Field label="Name" value={name} onChange={(e) => setName(e.target.value)} />
        <Field label="Email" type="email" value={email} readOnly />
        {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
        <Button loading={busy} disabled={!name.trim()} onClick={save}>Save profile</Button>
      </div></Card>
    </main>
  );
}
