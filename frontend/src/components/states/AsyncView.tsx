import { ReactNode } from 'react';
import { LoadingState, EmptyState, ErrorState } from './States';
export function AsyncView<T>({ state, reload, isEmpty, empty, children }: {
  state: { status: 'loading' } | { status: 'success'; data: T } | { status: 'error'; message: string };
  reload: () => void; isEmpty?: (d: T) => boolean; empty?: { title: string; body: string }; children: (d: T) => ReactNode;
}) {
  if (state.status === 'loading') return <LoadingState text="Loading..." />;
  if (state.status === 'error') return <ErrorState message={state.message} onRetry={reload} />;
  if (isEmpty?.(state.data) && empty) return <EmptyState {...empty} />;
  return <>{children(state.data)}</>;
}
