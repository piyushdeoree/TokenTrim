import { Html, Head, Main, NextScript } from 'next/document';
const initTheme = `(function(){try{var t=localStorage.getItem('theme');if(!t){t=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'}document.documentElement.classList.toggle('dark',t==='dark')}catch(e){}})()`;
export default function Document() {
  return (
    <Html lang="en" suppressHydrationWarning>
      <Head><link rel="icon" href="/logo.svg" /><script dangerouslySetInnerHTML={{ __html: initTheme }} /></Head>
      <body><Main /><NextScript /></body>
    </Html>
  );
}
