import { useEffect, useState } from 'react';
import { AsyncView } from '@/components/states/AsyncView';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { MemberTable } from '@/components/team/MemberTable';
import { InviteMemberModal } from '@/components/team/InviteMemberModal';
import { useToast } from '@/components/ui/Toast';
import { useTeam } from '@/hooks/useTeam';
import { load, send } from '@/services/data';
import { Field } from '@/components/ui/Field';
import { useAsync } from '@/hooks/useAsync';
import type { Role } from '@/types/team';
const PERMS: [string, string][] = [['Owner', 'Manage team, roles, invitations and projects'], ['Admin', 'Manage members and invitations'], ['Member', 'Analyze prompts and view projects']];
export default function Team() {
  const [teamId, setTeamId] = useState<number | null>(null); const [teams, setTeams] = useState<{id:number;name:string}[]>([]);
  const { state, reload } = useTeam(teamId); const [open, setOpen] = useState(false); const toast = useToast();
  const [inviteToken, setInviteToken] = useState('');
  const [teamName, setTeamName] = useState('');
  const [inviteRefresh, setInviteRefresh] = useState(0);
  const invitations = useAsync(async () => teamId ? load<{id:number;email:string;role:string;expires_at:string;accepted_at:string|null;revoked_at:string|null}[]>(`/teams/${teamId}/invitations`) : [], [teamId, inviteRefresh]);
  useEffect(() => { load<{id:number;name:string}[]>('/teams').then((t) => { setTeams(t); setTeamId(t[0]?.id ?? null); }).catch(() => setTeamId(null)); }, []);
  // The backend enforces real authorization; these calls may return 403.
  const act = async (fn: () => Promise<unknown>, ok: string) => { try { await fn(); toast(ok); reload(); } catch { toast('Action not allowed or failed. Please try again.'); } };
  return (
    <main className="mx-auto max-w-5xl space-y-4 p-4 lg:p-8">
      <div className="flex flex-wrap items-end justify-between gap-3"><h1 className="text-xl font-semibold">Team</h1><div className="flex flex-wrap items-end gap-2">{teams.length > 0 && <label className="text-sm">Team<select aria-label="Team" value={teamId ?? ''} onChange={(e) => setTeamId(Number(e.target.value))} className="ml-2 rounded border p-2 dark:bg-slate-950">{teams.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</select></label>}{!teams.length && <><Field label="New team name" value={teamName} onChange={(e) => setTeamName(e.target.value)} /><Button disabled={!teamName.trim()} onClick={async () => { try { const t = await send<{id:number;name:string}>('post', '/teams', {name:teamName.trim()}); setTeams([t]); setTeamId(t.id); setTeamName(''); reload(); } catch { toast('Unable to create team.'); } }}>Create team</Button></>}<Button disabled={!teamId} onClick={() => setOpen(true)}>Invite member</Button></div></div>
      <AsyncView state={state} reload={reload} isEmpty={(d) => !d.length} empty={{ title: 'No members', body: 'Invite teammates to share projects.' }}>
        {(m) => <MemberTable members={m}
          onRemove={(id) => window.confirm('Remove this member?') && teamId && act(() => send('delete', `/teams/${teamId}/members/${id}`, null), 'Member removed.')}
          onRole={(id: string, r: Role) => teamId && act(() => send('patch', `/teams/${teamId}/members/${id}`, { role: r }), 'Role updated.')} />}
      </AsyncView>
      <Card title="Role permissions"><dl className="space-y-1 text-sm">{PERMS.map(([r, d]) => <div key={r} className="flex gap-2"><dt className="w-20 font-medium">{r}</dt><dd>{d}</dd></div>)}</dl></Card>
      <Card title="Invitation response"><div className="flex flex-wrap items-end gap-2"><Field label="Invitation token" value={inviteToken} onChange={(e) => setInviteToken(e.target.value)} />
        <Button disabled={!inviteToken.trim()} onClick={() => act(async () => { await send('post', '/teams/invitations/accept', { token: inviteToken.trim() }); setInviteToken(''); }, 'Invitation accepted.')}>Accept</Button>
        <Button variant="ghost" disabled={!inviteToken.trim()} onClick={() => act(async () => { await send('post', '/teams/invitations/reject', { token: inviteToken.trim() }); setInviteToken(''); }, 'Invitation rejected.')}>Reject</Button></div></Card>
      {teamId && <Card title="Invitations"><AsyncView state={invitations.state} reload={invitations.reload} isEmpty={(x) => !x.length} empty={{title:'No invitations',body:'Invitations you create appear here.'}}>
        {(rows) => <ul className="space-y-2 text-sm">{rows.map((i) => { const status = i.accepted_at ? 'Accepted' : i.revoked_at ? 'Revoked' : new Date(i.expires_at) <= new Date() ? 'Expired' : 'Pending'; return <li key={i.id} className="flex items-center justify-between gap-3"><span>{i.email} · {i.role} · {status}</span>{status === 'Pending' && <Button variant="ghost" onClick={() => act(() => send('delete', `/teams/${teamId}/invitations/${i.id}`), 'Invitation revoked.')}>Revoke</Button>}</li>; })}</ul>}
      </AsyncView></Card>}
      {open && teamId && <InviteMemberModal teamId={teamId} onClose={() => setOpen(false)} onDone={() => { reload(); setInviteRefresh((n) => n + 1); }} />}
    </main>
  );
}
