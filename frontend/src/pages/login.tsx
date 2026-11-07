import { useRouter } from 'next/router';
import { AuthModal } from '@/components/auth/AuthModal';
export default function LoginPage() {
  const router = useRouter();
  return <AuthModal mode="login" onModeChange={(mode) => router.push(mode === 'register' ? '/register' : '/login')} onClose={() => router.push('/')} onSuccess={() => router.push('/dashboard')} />;
}
