import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Field } from '@/components/ui/Field';
import { useToast } from '@/components/ui/Toast';
import { useAuth } from '@/context/AuthContext';
export default function Profile() {
  const { user, updateUser } = useAuth(); const toast = useToast();
  const [name, setName] = useState(user?.name ?? ''); const [email, setEmail] = useState(user?.email ?? ''); const [img, setImg] = useState('');
  const bad = !/^\S+@\S+\.\S+$/.test(email);
  return (
    <main className="mx-auto max-w-2xl p-4 lg:p-8">
      <h1 className="mb-4 text-xl font-semibold">Profile</h1>
      <Card><div className="space-y-3">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        {img && <img src={img} alt="Profile preview" className="h-20 w-20 rounded-full object-cover" />}
        <Field label="Name" value={name} onChange={(e) => setName(e.target.value)} />
        <Field label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} error={bad ? 'Enter a valid email address.' : undefined} />
        <Field label="Profile image" type="file" accept="image/*" onChange={(e) => { const f = e.target.files?.[0]; if (f) setImg(URL.createObjectURL(f)); }} />
        <Button disabled={bad || !name.trim()} onClick={() => { updateUser({ name, email }); toast('Profile saved.'); }}>Save profile</Button>
      </div></Card>
    </main>
  );
}
