import { FormEvent, useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Field } from '@/components/ui/Field';
import { Button } from '@/components/ui/Button';
import type { ProviderDefinition } from '@/types/provider';
import { toSafeByokMessage } from '@/services/byok/errors';
import { IS_BYOK_DEMO_MODE } from '@/services/byok/adapter';

export function ProviderConnectionModal({ provider, onClose, onConnect }: {
  provider: ProviderDefinition; onClose: () => void; onConnect: (key: string) => Promise<void>;
}) {
  const [key, setKey] = useState('');
  const [visible, setVisible] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const submit = async (event: FormEvent) => {
    event.preventDefault(); setError(null);
    if (key.trim().length < 8) { setError('Enter an API key with at least 8 characters.'); return; }
    setLoading(true);
    try { await onConnect(key.trim()); setKey(''); onClose(); }
    catch (e) { setError(toSafeByokMessage(e, 'Unable to connect this provider.', [key.trim()])); }
    finally { setKey(''); setLoading(false); }
  };
  return <Modal title={`Connect ${provider.name}`} onClose={onClose}>
    <p className="mb-4 text-sm opacity-75">{IS_BYOK_DEMO_MODE ? 'Your key is submitted to the local demo adapter for this session. It is not saved or sent to the provider.' : 'Your key is submitted only to the TokenTrim backend service over the configured API connection.'}</p>
    <form onSubmit={submit} className="space-y-4">
      <Field label="API key" type={visible ? 'text' : 'password'} autoComplete="off" value={key} onChange={(e) => setKey(e.target.value)} aria-invalid={!!error} placeholder="Paste your API key" aria-describedby={error ? 'byok-key-error byok-key-note' : 'byok-key-note'} />
      <p id="byok-key-note" className="text-xs opacity-70">The key stays in memory only while this form is open.</p>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={visible} onChange={(e) => setVisible(e.target.checked)} /> Show API key</label>
      {error && <p id="byok-key-error" role="alert" className="text-sm text-red-700 dark:text-red-400">{error}</p>}
      <div className="flex flex-wrap justify-end gap-2"><Button variant="ghost" onClick={onClose} disabled={loading}>Cancel</Button><Button type="submit" loading={loading}>Connect provider</Button></div>
    </form>
  </Modal>;
}
