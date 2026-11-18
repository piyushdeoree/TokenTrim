import type { AppProps } from 'next/app';
import { useRouter } from 'next/router';
import { useEffect } from 'react';
import '@/styles/globals.css';
import { AuthProvider, useAuth } from '@/context/AuthContext';
import { ThemeProvider } from '@/context/ThemeContext';
import { CurrencyProvider } from '@/context/CurrencyContext';
import { ToastProvider } from '@/components/ui/Toast';
import { AppLayout } from '@/layouts/AppLayout';
import { LoadingState } from '@/components/states/States';
import { ProviderProvider } from '@/context/ProviderContext';
const PUBLIC = ['/', '/login', '/register'];
function Shell({ Component, pageProps }: AppProps) {
  const { pathname, replace } = useRouter();
  const { user, ready } = useAuth();
  const isPublic = PUBLIC.includes(pathname);
  useEffect(() => { if (ready && !user && !isPublic) replace('/?auth=login'); }, [ready, user, isPublic, replace]);
  if (!ready || (!user && !isPublic)) return <LoadingState text="Loading..." />;
  const page = <AppLayout><Component {...pageProps} /></AppLayout>;
  return user ? <ProviderProvider>{page}</ProviderProvider> : page;
}
export default function App(props: AppProps) {
  return <CurrencyProvider><ThemeProvider><ToastProvider><AuthProvider><Shell {...props} /></AuthProvider></ToastProvider></ThemeProvider></CurrencyProvider>;
}
