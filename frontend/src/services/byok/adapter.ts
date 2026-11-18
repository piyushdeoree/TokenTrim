import type { ExecutionAdapter } from '@/types/execution';
import { createDemoAdapter } from './demoAdapter';

const canUseDevelopmentDemo = process.env.NODE_ENV === 'development' || process.env.NODE_ENV === 'test';
export const IS_BYOK_DEMO_MODE = process.env.NEXT_PUBLIC_BYOK_MODE === 'demo'
  || (process.env.NEXT_PUBLIC_BYOK_MODE !== 'real' && canUseDevelopmentDemo);
let adapter: ExecutionAdapter | undefined;

/** Install an adapter after a real backend contract is agreed. */
export function configureByokAdapter(next: ExecutionAdapter | null) {
  adapter = next ?? undefined;
}

export function isByokAvailable() {
  return IS_BYOK_DEMO_MODE || !!adapter;
}

export function getByokAdapter(): ExecutionAdapter {
  if (!IS_BYOK_DEMO_MODE) {
    if (adapter) return adapter;
    throw new Error('BYOK backend integration is not configured.');
  }
  adapter ??= createDemoAdapter();
  return adapter;
}
