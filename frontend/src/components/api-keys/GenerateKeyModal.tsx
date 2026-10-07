import { useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Field } from '@/components/ui/Field';
import { useCopyToClipboard } from '@/hooks/useCopyToClipboard';
import { send } from '@/services/data';
import type { NewApiKey } from '@/types/apiKey';
export function GenerateKeyModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const [name, setName] = useState(''); const [secret, setSecret] = useState(''); const [err, setErr] = useState('');
  const { copied, copy } = useCopyToClipboard();
  const generate = async () => {
    try { setSecret((await send<NewApiKey>('post', '/api/api-keys', { name }, { secret: 'tt_live_mock_secret_shown_once' })).secret); onDone(); }
    catch { setErr('Unable to generate key. Please try again.'); }
  };
  return (
    <Modal title="Generate key" onClose={onClose}>
      {!secret ? (<><Field label="Key name" value={name} onChange={(e) => setName(e.target.value)} error={err} />
        <Button className="mt-4" disabled={!name.trim()} onClick={generate}>Generate key</Button></>)
        : (<><p className="text-sm">Copy this key now. It will not be shown again.</p>
          <code className="mt-2 block break-all rounded bg-slate-100 p-2 text-xs dark:bg-slate-800">{secret}</code>
          <div className="mt-4 flex gap-2"><Button onClick={() => copy(secret)}>{copied ? 'Copied' : 'Copy key'}</Button><Button variant="ghost" onClick={onClose}>Done</Button></div></>)}
    </Modal>
  );
}
