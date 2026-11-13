import { Select } from '@/components/ui/Select';
import { ROLES } from '@/utils/constants';
import type { Role } from '@/types/team';
export const RoleSelect = ({ value, onChange, label = 'Role', allowOwner }: { value: Role; onChange: (r: Role) => void; label?: string; allowOwner?: boolean }) => (
  <Select label={label} value={value} onChange={(e) => onChange(e.target.value as Role)}>
    {ROLES.map((r) => r.toLowerCase()).filter((r) => allowOwner || r !== 'owner').map((r) => <option key={r} value={r}>{r}</option>)}</Select>
);
