import { useState } from 'react';
export function useCopyToClipboard() {
  const [copied, setCopied] = useState(false);
  const copy = async (text: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(true); setTimeout(() => setCopied(false), 1800);
  };
  return { copied, copy };
}
