import { DataTable } from '@/components/ui/DataTable';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import type { Member, Role } from '@/types/team';
export const MemberTable = ({ members, onRemove, onRole }: { members: Member[]; onRemove: (id: string) => void; onRole: (id: string, r: Role) => void }) => (
  <DataTable caption="Team members" rows={members} cols={[
    { header: 'Name', cell: (m) => m.name }, { header: 'Email', cell: (m) => m.email },
    { header: 'Role', cell: (m) => m.role === 'Owner' ? <Badge tone="good">Owner</Badge> :
      <select aria-label={`Role for ${m.name}`} value={m.role} onChange={(e) => onRole(m.id, e.target.value as Role)} className="rounded border p-1 text-sm dark:bg-slate-950"><option>Admin</option><option>Member</option></select> },
    { header: 'Actions', cell: (m) => m.role === 'Owner' ? '—' : <Button variant="ghost" onClick={() => onRemove(m.id)} aria-label={`Remove ${m.name}`}>Remove</Button> }]} />
);
