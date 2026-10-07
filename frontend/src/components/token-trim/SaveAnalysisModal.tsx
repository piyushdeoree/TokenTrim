import { useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { useToast } from '@/components/ui/Toast';
import { useProjects } from '@/hooks/useProjects';
import { send } from '@/services/data';
import type { AnalyzePromptResponse } from '@/types/analysis';
export function SaveAnalysisModal({ prompt, model, result, onClose }: { prompt: string; model: string; result: AnalyzePromptResponse; onClose: () => void }) {
  const { state } = useProjects(); const toast = useToast();
  const [pid, setPid] = useState(''); const [msg, setMsg] = useState(''); const [busy, setBusy] = useState(false);
  const save = async () => {
    if (!pid) return setMsg('Select a project.');
    setBusy(true);
    try { await send('post', '/api/analyses', { project_id: pid, prompt, model, result }, {}); toast('Analysis saved.'); onClose(); }
    catch { setMsg('Unable to save analysis. Please try again.'); } finally { setBusy(false); }
  };
  return (
    <Modal title="Save analysis" onClose={onClose}>
      <Select label="Project" value={pid} onChange={(e) => setPid(e.target.value)}>
        <option value="">Select a project</option>
        {state.status === 'success' && state.data.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
      </Select>
      {msg && <p role="alert" className="mt-2 text-sm text-red-700 dark:text-red-400">{msg}</p>}
      <div className="mt-4 flex gap-2"><Button loading={busy} onClick={save}>Save analysis</Button><Button variant="ghost" onClick={onClose}>Close</Button></div>
    </Modal>
  );
}
