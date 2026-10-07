import { useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Field } from '@/components/ui/Field';
import { RoleSelect } from './RoleSelect';
import { send } from '@/services/data';
import type { Role } from '@/types/team';
export function InviteMemberModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const [email, setEmail] = useState(''); const [role, setRole] = useState<Role>('Member'); const [err, setErr] = useState('');
  const invite = async () => {
    if (!/^\S+@\S+\.\S+$/.test(email)) return setErr('Enter a valid email address.');
    try { await send('post', '/api/team/invite', { email, role }, {}); onDone(); onClose(); } catch { setErr('Unable to send invite. Please try again.'); }
  };
  return (
    <Modal title="Invite member" onClose={onClose}>
      <div className="space-y-3"><Field label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} error={err} /><RoleSelect value={role} onChange={setRole} /></div>
      <Button className="mt-4" onClick={invite}>Send invite</Button>
    </Modal>
  );
}
