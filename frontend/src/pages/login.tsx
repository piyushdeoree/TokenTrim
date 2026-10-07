
import { useState } from 'react';
import { useRouter } from 'next/router';
import { AuthModal, AuthMode } from '@/components/auth/AuthModal';

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<AuthMode>('login');

  return (
    <AuthModal
      mode={mode}
      onModeChange={setMode}
      onClose={() => router.replace('/')}
      onSuccess={() => router.push('/dashboard')}
    />
  );
}