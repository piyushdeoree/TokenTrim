import { useCallback, useEffect, useRef, useState } from 'react';
type S<T> = { status: 'loading' } | { status: 'success'; data: T } | { status: 'error'; message: string };
// deps: re-fetch when they change (e.g. dashboard date range). Stale responses are ignored.
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[] = [], errorText = 'Unable to load data. Please try again.') {
  const [state, setState] = useState<S<T>>({ status: 'loading' });
  const req = useRef(0);
  const reload = useCallback(() => {
    const id = ++req.current;
    setState({ status: 'loading' });
    fn().then((data) => id === req.current && setState({ status: 'success', data }))
      .catch(() => id === req.current && setState({ status: 'error', message: errorText }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  useEffect(reload, [reload]);
  return { state, reload, setState };
}
