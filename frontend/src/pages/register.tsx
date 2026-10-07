import { useEffect } from 'react';
import { useRouter } from 'next/router';
// Auth now lives in a modal on the Home page; keep old URLs working.
export default function RegisterRedirect() {
  const router = useRouter();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { router.replace('/?auth=register'); }, []);
  return null;
}
