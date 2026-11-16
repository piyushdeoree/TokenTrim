import { Button } from '@/components/ui/Button';
export const AnalyzeButton = ({ onClick, loading }: { onClick: () => void; loading: boolean }) =>
  <Button onClick={onClick} loading={loading}>{loading ? 'Analyzing...' : 'Analyze prompt'}</Button>;
