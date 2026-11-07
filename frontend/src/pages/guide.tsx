const S = [
  ['How to analyze a prompt', 'Paste your prompt in Token Trim, choose the model you plan to call, and select Analyze prompt.'],
  ['How token costs work', 'Providers charge per token, with separate rates for input and output. Longer prompts and longer answers both cost more.'],
  ['How optimization works', 'Token Trim finds repeated instructions, extra context and wordy phrasing, then proposes a shorter prompt with the same intent.'],
  ['How to interpret savings', 'Tokens saved is the drop in prompt length. Potential saving is the estimated cost difference per call; multiply it by your call volume.'],
];
export default function Guide() {
  return (<main className="mx-auto max-w-3xl space-y-6 p-4 lg:p-8"><h1 className="text-xl font-semibold">Guide</h1>
    {S.map(([h, b]) => <section key={h}><h2 className="font-semibold">{h}</h2><p className="mt-1 text-sm leading-relaxed">{b}</p></section>)}</main>);
}
