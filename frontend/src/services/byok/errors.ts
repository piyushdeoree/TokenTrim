import axios from 'axios';

const credentialPatterns = [
  /\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{12,}\b/gi,
  /\bAIza[A-Za-z0-9_-]{20,}\b/g,
];

export function redactKnownCredentials(value: string) {
  return credentialPatterns.reduce((text, pattern) => text.replace(pattern, '[redacted credential]'), value);
}

export function toSafeByokMessage(error: unknown, fallback: string, secrets: string[] = []) {
  const raw = axios.isAxiosError(error)
    ? String(error.response?.data?.detail ?? error.message ?? '')
    : error instanceof Error ? error.message : '';
  if (!raw) return fallback;
  let safe = raw;
  for (const secret of secrets.filter(Boolean)) safe = safe.split(secret).join('[redacted]');
  return redactKnownCredentials(safe).trim() || fallback;
}

export function sanitizeProviderConnection(input: unknown) {
  if (!input || typeof input !== 'object') throw new Error('Provider service returned an invalid connection.');
  const value = input as Record<string, unknown>;
  const validProviders = ['openai', 'gemini', 'anthropic'];
  if (!validProviders.includes(String(value.provider)) || !['connected', 'disconnected'].includes(String(value.status))) {
    throw new Error('Provider service returned an invalid connection.');
  }
  const maskedKey = typeof value.maskedKey === 'string' && /^[•*xX-]{4,}[A-Za-z0-9]{0,4}$/.test(value.maskedKey)
    ? value.maskedKey : undefined;
  return {
    provider: value.provider as 'openai' | 'gemini' | 'anthropic',
    status: value.status as 'connected' | 'disconnected',
    connectedAt: typeof value.connectedAt === 'string' && Number.isFinite(Date.parse(value.connectedAt)) ? value.connectedAt : '',
    ...(maskedKey ? { maskedKey } : {}),
  };
}
