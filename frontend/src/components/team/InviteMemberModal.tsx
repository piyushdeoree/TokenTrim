import { useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Field } from '@/components/ui/Field';
import { RoleSelect } from './RoleSelect';
import { send } from '@/services/data';
import type { Role } from '@/types/team';
export function InviteMemberModal({ teamId, onClose, onDone }: { teamId: number; onClose: () => void; onDone: () => void }) {
  const [email, setEmail] = useState(''); const [role, setRole] = useState<Role>('member'); const [err, setErr] = useState(''); const [token, setToken] = useState('');
  const invite = async () => {
    if (!/^\S+@\S+\.\S+$/.test(email)) return setErr('Enter a valid email address.');
    try { const invite = await send<{token:string}>('post', `/teams/${teamId}/invitations`, { email, role }); setToken(invite.token); onDone(); } catch { setErr('Unable to create invitation. Check team permissions and try again.'); }
  };
  return (
    <Modal title="Invite member" onClose={onClose}>
      {!token ? <><div className="space-y-3"><Field label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} error={err} /><RoleSelect value={role} onChange={setRole} /></div>
        <Button className="mt-4" onClick={invite}>Create invitation</Button></>
        : <div className="space-y-3 text-sm"><p>Invitation created and saved. Email delivery is not configured; share this one time token securely with the invited person. It expires in 7 days.</p><code className="block break-all rounded bg-black/5 p-3 dark:bg-white/5">{token}</code><Button onClick={onClose}>Done</Button></div>}
    </Modal>
  );
}
