import { useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Field } from '@/components/ui/Field';
import { send } from '@/services/data';
export function CreateProjectModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [name, setName] = useState(''); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false);
  const create = async () => {
    if (name.trim().length < 2) return setErr('Project name must be at least 2 characters.');
    setBusy(true);
    try { await send('post', '/api/projects', { name }, {}); onCreated(); onClose(); }
    catch { setErr('Unable to create project. Please try again.'); } finally { setBusy(false); }
  };
  return (
    <Modal title="Create project" onClose={onClose}>
      <Field label="Project name" value={name} onChange={(e) => setName(e.target.value)} error={err} />
      <div className="mt-4 flex gap-2"><Button loading={busy} onClick={create}>Create project</Button><Button variant="ghost" onClick={onClose}>Cancel</Button></div>
    </Modal>
  );
}
