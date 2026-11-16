import { DataTable } from '@/components/ui/DataTable';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import type { Member, Role } from '@/types/team';
export const MemberTable = ({ members, onRemove, onRole }: { members: Member[]; onRemove: (id: string) => void; onRole: (id: string, r: Role) => void }) => (
  <DataTable caption="Team members" rows={members} cols={[
    { header: 'Name', cell: (m) => m.full_name }, { header: 'Email', cell: (m) => m.email },
    { header: 'Role', cell: (m) => m.role === 'owner' ? <Badge tone="good">Owner</Badge> :
      <select aria-label={`Role for ${m.full_name}`} value={m.role} onChange={(e) => onRole(String(m.user_id), e.target.value as Role)} className="rounded border p-1 text-sm dark:bg-slate-950"><option value="admin">Admin</option><option value="member">Member</option></select> },
    { header: 'Actions', cell: (m) => m.role === 'owner' ? '—' : <Button variant="ghost" onClick={() => onRemove(String(m.user_id))} aria-label={`Remove ${m.full_name}`}>Remove</Button> }]} />
);
