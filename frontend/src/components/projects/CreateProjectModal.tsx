import { useEffect, useMemo, useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Field } from '@/components/ui/Field';
import { send } from '@/services/data';
import { questions, visibleQuestions, pruneAnswers, pruneCustomAnswers, hasAnswer, hasOtherSelection, requirementsFrom, type Answer, type Answers, type CustomAnswers, type Question } from './questionnaire';

const DRAFT_KEY = 'tokentrim:project-questionnaire:draft';
const LEGACY_OTHER_ANSWERS: Record<string, string> = {
  categoryOther: 'category', webKindOther: 'webKind', mobileApproachOther: 'mobileApproach',
  frontendOther: 'frontend', languageOther: 'language', authOther: 'authMethods', deploymentOther: 'deployment',
};
type Draft = { name: string; answers: Answers; customAnswers?: CustomAnswers; step: string };
type CreatedProject = { id: number; name: string };

export function CreateProjectModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [name, setName] = useState('');
  const [answers, setAnswers] = useState<Answers>({});
  const [customAnswers, setCustomAnswers] = useState<CustomAnswers>({});
  const [step, setStep] = useState('name');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);
  const [returnToReview, setReturnToReview] = useState(false);
  const flow = useMemo(() => visibleQuestions(answers), [answers]);
  const review = step === 'review';
  const currentIndex = flow.findIndex(q => q.id === step);
  const current = flow[currentIndex];

  useEffect(() => {
    try {
      const saved = localStorage.getItem(DRAFT_KEY);
      if (saved) {
        const draft = JSON.parse(saved) as Draft;
        if (draft && typeof draft.name === 'string' && draft.answers) {
          setName(draft.name);
          const legacyCustom = { ...(draft.customAnswers ?? {}) };
          Object.entries(LEGACY_OTHER_ANSWERS).forEach(([oldId, questionId]) => {
            if (typeof draft.answers[oldId] === 'string') legacyCustom[questionId] = draft.answers[oldId] as string;
          });
          const valid = pruneAnswers(Object.fromEntries(Object.entries(draft.answers).filter(([id]) => questions.some(q => q.id === id))));
          const validCustom = pruneCustomAnswers(valid, legacyCustom);
          setAnswers(valid);
          setCustomAnswers(validCustom);
          const applicable = visibleQuestions(valid);
          const step = LEGACY_OTHER_ANSWERS[draft.step] ?? draft.step;
          setStep(step === 'review' ? 'review' : step === 'name' ? 'name' : applicable.some(q => q.id === step) ? step : 'name');
        }
      }
    } catch { /* Ignore an unreadable draft. */ }
    setReady(true);
  }, []);

  useEffect(() => {
    if (!ready) return;
    try { localStorage.setItem(DRAFT_KEY, JSON.stringify({ name, answers, customAnswers, step } satisfies Draft)); } catch { /* Storage is optional. */ }
  }, [name, answers, customAnswers, step, ready]);

  const putAnswer = (id: string, value: Answer) => {
    const next = pruneAnswers({ ...answers, [id]: value });
    setAnswers(next);
    setCustomAnswers(previous => pruneCustomAnswers(next, previous));
    setError('');
  };

  const putCustomAnswer = (id: string, value: string) => {
    setCustomAnswers(previous => pruneCustomAnswers(answers, { ...previous, [id]: value }));
    setError('');
  };

  const advance = () => {
    if (step === 'name') {
      if (name.trim().length < 2) return setError('Project name must be at least 2 characters.');
      setError('');
      if (returnToReview) { setReturnToReview(false); setStep('review'); }
      else setStep(flow[0]?.id ?? 'review');
      return;
    }
    if (!current) return;
    const value = answers[current.id];
    if (current.required && !hasAnswer(value)) return setError('Please provide an answer before continuing.');
    if (hasOtherSelection(current, answers) && !hasAnswer(customAnswers[current.id])) return setError('Please enter a custom answer for Other before continuing.');
    const nextStep = flow[currentIndex + 1]?.id ?? 'review';
    setError(''); setStep(nextStep);
    if (returnToReview && nextStep === 'review') setReturnToReview(false);
  };

  const skip = () => {
    if (!current) return;
    if (hasOtherSelection(current, answers) && !hasAnswer(customAnswers[current.id])) return setError('Please enter a custom answer for Other before continuing.');
    const nextStep = flow[currentIndex + 1]?.id ?? 'review';
    setStep(nextStep);
    setError('');
    if (returnToReview && nextStep === 'review') setReturnToReview(false);
  };

  const back = () => {
    setError('');
    if (review) { setStep(flow[flow.length - 1]?.id ?? 'name'); return; }
    if (step === 'name') return;
    setStep(currentIndex <= 0 ? 'name' : flow[currentIndex - 1].id);
  };

  const select = (q: Question, value: string) => {
    if (q.kind === 'multi') {
      const selected = Array.isArray(answers[q.id]) ? [...answers[q.id] as string[]] : [];
      putAnswer(q.id, selected.includes(value) ? selected.filter(v => v !== value) : [...selected, value]);
      return;
    }
    putAnswer(q.id, value);
    if (value !== 'Other' && q.kind === 'choice') {
      const nextAnswers = pruneAnswers({ ...answers, [q.id]: value });
      const applicable = visibleQuestions(nextAnswers);
      const nextStep = applicable[applicable.findIndex(item => item.id === q.id) + 1]?.id ?? 'review';
      setStep(nextStep);
      if (returnToReview && nextStep === 'review') setReturnToReview(false);
    }
  };

  const create = async () => {
    setBusy(true); setError('');
    try {
      const created = await send<CreatedProject>('post', '/projects', { name: name.trim() });
      try {
        localStorage.setItem(`tokentrim:project-requirements:${created.id}`, JSON.stringify(requirementsFrom(answers, name, customAnswers)));
        localStorage.removeItem(DRAFT_KEY);
      } catch { /* Project creation remains successful if browser storage is unavailable. */ }
      onCreated(); onClose();
    } catch { setError('Unable to create project. Please try again.'); }
    finally { setBusy(false); }
  };

  const renderQuestion = (q: Question) => {
    const value = answers[q.id];
    return <div className="space-y-4" key={q.id}>
      <div><h3 className="text-lg font-semibold">{q.prompt}</h3>{q.help && <p className="mt-1 text-sm opacity-70">{q.help}</p>}<p className="mt-1 text-xs opacity-60">{q.required ? 'Required' : 'Optional — you can skip this'}</p></div>
      {q.kind === 'choice' || q.kind === 'multi' ? <div role={q.kind === 'multi' ? 'group' : undefined} aria-label={q.prompt} className="grid gap-2 sm:grid-cols-2">
        {q.options?.map(option => {
          const selected = Array.isArray(value) ? value.includes(option) : value === option;
          return <button key={option} type="button" aria-pressed={selected} onClick={() => select(q, option)} className={`min-h-12 rounded-md border px-3 py-3 text-left text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900 dark:focus-visible:outline-btn ${selected ? 'border-teal-700 bg-teal-700/10 font-medium dark:border-teal-400' : 'border-slate-300 hover:bg-black/5 dark:border-slate-600 dark:hover:bg-white/5'}`}>{option}</button>;
        })}
      </div> : <label className="block"><span className="sr-only">{q.prompt}</span>{q.kind === 'long' ? <textarea aria-label={q.prompt} rows={5} maxLength={4000} value={String(value ?? '')} onChange={e => putAnswer(q.id, e.target.value)} placeholder="Write a few details…" className="w-full resize-y rounded-md border border-slate-300 bg-white p-3 text-sm dark:border-slate-600 dark:bg-slate-950" /> : <input aria-label={q.prompt} value={String(value ?? '')} onChange={e => putAnswer(q.id, e.target.value)} placeholder="Type your answer…" className="w-full rounded-md border border-slate-300 bg-white p-3 text-sm dark:border-slate-600 dark:bg-slate-950" />}</label>}
      {(q.kind === 'choice' || q.kind === 'multi') && hasOtherSelection(q, answers) && <Field label="Your answer for Other" value={customAnswers[q.id] ?? ''} onChange={e => putCustomAnswer(q.id, e.target.value)} placeholder="Tell us what you have in mind" />}
      {q.kind === 'multi' && <p className="text-xs opacity-65">Select all that apply, then continue.</p>}
    </div>;
  };

  const shownCount = step === 'name' ? 0 : Math.max(0, currentIndex + 1);
  return <Modal title="Create a project" onClose={onClose}>
    <div className="mb-5" aria-label="Questionnaire progress">
      <div className="flex justify-between gap-3 text-xs opacity-70"><span>{review ? 'Review requirements' : step === 'name' ? 'Project details' : `Question ${shownCount}`}</span><span>{review ? 'Ready to submit' : 'The next questions depend on your answers'}</span></div>
    </div>
    {step === 'name' && <div className="space-y-4"><div><h3 className="text-lg font-semibold">Let’s start with a name for your project.</h3><p className="mt-1 text-sm opacity-70">You can change it later.</p></div><Field label="Project name" autoFocus value={name} onChange={e => { setName(e.target.value); setError(''); }} error={error} placeholder="e.g. Customer insights dashboard" /></div>}
    {!review && step !== 'name' && current && renderQuestion(current)}
    {review && <div className="max-h-[52vh] space-y-5 overflow-y-auto pr-1"><div><h3 className="text-lg font-semibold">Review your project requirements</h3><p className="mt-1 text-sm opacity-70">You can go back to change any answer before creating the project.</p></div>
      <section><h4 className="mb-2 font-semibold">Project</h4><div className="flex items-center justify-between gap-3 rounded-md border border-slate-300 p-3 text-sm dark:border-slate-600"><div className="min-w-0"><span className="opacity-70">Name</span><div className="break-words font-medium">{name}</div></div><Button variant="ghost" aria-label="Edit project name" className="min-h-11 shrink-0" onClick={() => { setReturnToReview(true); setStep('name'); }}>Edit</Button></div></section>
      {requirementsFrom(answers, name, customAnswers).sections.filter(section => section.items.length).map(section => <section key={section.title}><h4 className="mb-2 font-semibold">{section.title}</h4><dl className="space-y-2">{section.items.map(item => <div key={item.id} className="flex items-center justify-between gap-3 rounded-md border border-slate-300 p-3 text-sm dark:border-slate-600"><div className="min-w-0"><dt className="text-xs opacity-65">{item.question}</dt><dd className="mt-1 break-words whitespace-pre-wrap">{Array.isArray(item.answer) ? item.answer.join(', ') : item.answer}</dd></div><Button variant="ghost" aria-label={`Edit ${item.question}`} className="min-h-11 shrink-0" onClick={() => { setReturnToReview(true); setStep(item.id); }}>Edit</Button></div>)}</dl></section>)}
    </div>}
    {error && step !== 'name' && <p role="alert" className="mt-3 text-sm text-red-700 dark:text-red-400">{error}</p>}
    <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:items-center sm:justify-between">
      <Button variant="ghost" className="min-h-12 w-full sm:w-auto" onClick={back} disabled={step === 'name' || busy}>Previous</Button>
      <div className="grid grid-cols-2 gap-2 sm:flex sm:gap-2">{!review && current && !current.required && <Button variant="ghost" className="min-h-12 w-full px-3 whitespace-normal leading-tight" onClick={skip}>Skip</Button>}
        {review ? <Button loading={busy} className="min-h-12 w-full px-3 whitespace-normal leading-tight" onClick={create}>Submit requirements</Button> : <Button className="min-h-12 w-full px-3 whitespace-normal leading-tight" onClick={advance}>Continue</Button>}
        <Button variant="ghost" className="min-h-12 w-full px-3 whitespace-normal leading-tight" onClick={onClose} disabled={busy}>Cancel</Button></div>
    </div>
  </Modal>;
}
