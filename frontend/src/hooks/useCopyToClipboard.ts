import { useEffect, useRef, useState } from 'react';
export function useCopyToClipboard() {
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const resetTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => {
    if (resetTimer.current) clearTimeout(resetTimer.current);
  }, []);

  const fallbackCopy = (text: string) => {
    const field = document.createElement('textarea');
    field.value = text;
    field.setAttribute('readonly', '');
    field.style.position = 'fixed';
    field.style.opacity = '0';
    document.body.appendChild(field);
    field.select();
    try { return document.execCommand('copy'); }
    finally { document.body.removeChild(field); }
  };

  const copy = async (text: string) => {
    setCopied(false);
    setError(null);
    try {
      if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(text);
      else if (!fallbackCopy(text)) throw new Error('Clipboard copy was declined.');
    } catch {
      try {
        if (!fallbackCopy(text)) throw new Error('Clipboard copy was declined.');
      } catch {
        setError('Unable to copy automatically. Select and copy the text manually.');
        return;
      }
    }
    setCopied(true);
    if (resetTimer.current) clearTimeout(resetTimer.current);
    resetTimer.current = setTimeout(() => setCopied(false), 1800);
  };
  return { copied, error, copy };
}
