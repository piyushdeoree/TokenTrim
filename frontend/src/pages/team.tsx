import { useState } from 'react';
import { AsyncView } from '@/components/states/AsyncView';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { MemberTable } from '@/components/team/MemberTable';
import { InviteMemberModal } from '@/components/team/InviteMemberModal';
import { useToast } from '@/components/ui/Toast';
import { useTeam } from '@/hooks/useTeam';
import { send } from '@/services/data';
import type { Role } from '@/types/team';
const PERMS: [string, string][] = [['Owner', 'Full access, billing, delete team'], ['Admin', 'Manage members, API keys and projects'], ['Member', 'Analyze prompts and view projects']];
export default function Team() {
  const { state, reload } = useTeam(); const [open, setOpen] = useState(false); const toast = useToast();
  // The backend enforces real authorization; these calls may return 403.
  const act = async (fn: () => Promise<unknown>, ok: string) => { try { await fn(); toast(ok); reload(); } catch { toast('Action not allowed or failed. Please try again.'); } };
  return (
    <main className="mx-auto max-w-5xl space-y-4 p-4 lg:p-8">
      <div className="flex items-center justify-between"><h1 className="text-xl font-semibold">Team</h1><Button onClick={() => setOpen(true)}>Invite member</Button></div>
      <AsyncView state={state} reload={reload} isEmpty={(d) => !d.length} empty={{ title: 'No members', body: 'Invite teammates to share projects.' }}>
        {(m) => <MemberTable members={m}
          onRemove={(id) => window.confirm('Remove this member?') && act(() => send('delete', `/api/team/${id}`, null, {}), 'Member removed.')}
          onRole={(id: string, r: Role) => act(() => send('post', `/api/team/${id}/role`, { role: r }, {}), 'Role updated.')} />}
      </AsyncView>
      <Card title="Role permissions"><dl className="space-y-1 text-sm">{PERMS.map(([r, d]) => <div key={r} className="flex gap-2"><dt className="w-20 font-medium">{r}</dt><dd>{d}</dd></div>)}</dl></Card>
      {open && <InviteMemberModal onClose={() => setOpen(false)} onDone={reload} />}
    </main>
  );
}
