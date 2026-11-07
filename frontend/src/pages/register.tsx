import { useRouter } from 'next/router';
import { AuthModal } from '@/components/auth/AuthModal';
export default function RegisterPage() {
  const router = useRouter();
  return <AuthModal mode="register" onModeChange={(mode) => router.push(mode === 'register' ? '/register' : '/login')} onClose={() => router.push('/')} onSuccess={() => router.push('/dashboard')} />;
}
