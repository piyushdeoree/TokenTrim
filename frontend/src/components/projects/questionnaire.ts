export type Answer = string | string[];
export type Answers = Record<string, Answer>;
export type CustomAnswers = Record<string, string>;
export type Question = {
  id: string;
  prompt: string;
  help?: string;
  kind: 'choice' | 'multi' | 'text' | 'long';
  options?: string[];
  required?: boolean;
  visible?: (answers: Answers) => boolean;
};
export type CollectedRequirements = {
  name: string;
  answers: Answers;
  customAnswers: CustomAnswers;
  sections: { title: string; items: { id: string; question: string; answer: Answer }[] }[];
};

export const projectTypes = [
  'Web Application', 'Mobile Application', 'AI / Machine Learning',
  'Desktop Application', 'API / Backend Service', 'Data Analytics', 'Other',
];

const appCategories = ['Web Application', 'Mobile Application', 'Desktop Application'];

export const questions: Question[] = [
  { id: 'category', prompt: 'What are you planning to build?', help: 'This helps tailor the next few questions to your project.', kind: 'choice', options: projectTypes, required: true },
  { id: 'webKind', prompt: 'What kind of web application is it?', kind: 'choice', options: ['E-commerce', 'Portfolio', 'SaaS platform', 'Dashboard', 'Social platform', 'Other'], visible: a => a.category === 'Web Application' },
  { id: 'platform', prompt: 'Which platforms should your app support?', kind: 'multi', options: ['Android', 'iOS', 'Both Android and iOS'], visible: a => a.category === 'Mobile Application' },
  { id: 'mobileApproach', prompt: 'How would you like to build the mobile app?', kind: 'choice', options: ['Native', 'Cross-platform', 'Not sure yet', 'Other'], visible: a => a.category === 'Mobile Application' },
  { id: 'problem', prompt: 'What problem should your AI or data project solve?', help: 'A short description is enough to get started.', kind: 'long', required: true, visible: a => ['AI / Machine Learning', 'Data Analytics'].includes(String(a.category)) },
  { id: 'model', prompt: 'Do you have a model or algorithm in mind?', kind: 'choice', options: ['Yes', 'No', 'Not sure yet'], visible: a => a.category === 'AI / Machine Learning' },
  { id: 'modelDetails', prompt: 'Which model or algorithm are you considering?', kind: 'text', required: true, visible: a => a.model === 'Yes' && a.category === 'AI / Machine Learning' },
  { id: 'dataset', prompt: 'Do you already have a dataset?', kind: 'choice', options: ['Yes', 'No', 'Not sure yet'], visible: a => a.category === 'AI / Machine Learning' || a.category === 'Data Analytics' },
  { id: 'datasetDetails', prompt: 'Where is your dataset, and is it ready to use?', kind: 'text', required: true, visible: a => a.dataset === 'Yes' && (a.category === 'AI / Machine Learning' || a.category === 'Data Analytics') },
  { id: 'frontend', prompt: 'Which frontend technology would you prefer?', kind: 'choice', options: ['React', 'Next.js', 'Angular', 'Vue', 'HTML / CSS / JavaScript', 'Not decided yet', 'Other'], visible: a => a.category === 'Web Application' || a.category === 'Mobile Application' },
  { id: 'language', prompt: 'Which programming language do you prefer?', kind: 'choice', options: ['Python', 'JavaScript / TypeScript', 'Java', 'C#', 'Not decided yet', 'Other'], visible: a => ['AI / Machine Learning', 'Desktop Application', 'API / Backend Service', 'Data Analytics'].includes(String(a.category)) },
  { id: 'backend', prompt: 'Will your project need a backend?', kind: 'choice', options: ['Yes', 'No', 'Not sure yet'], visible: a => ['Web Application', 'Mobile Application', 'Desktop Application'].includes(String(a.category)) },
  { id: 'auth', prompt: 'Will users need to sign in?', kind: 'choice', options: ['Yes', 'No', 'Not sure yet'], visible: a => appCategories.includes(String(a.category)) && a.backend === 'Yes' },
  { id: 'authMethods', prompt: 'Which sign-in methods do you need?', kind: 'multi', options: ['Email and password', 'Google login', 'One-time code (OTP)', 'Role-based access', 'Other'], visible: a => appCategories.includes(String(a.category)) && a.backend === 'Yes' && a.auth === 'Yes' },
  { id: 'database', prompt: 'Do you already have a database?', kind: 'choice', options: ['Yes', 'No', 'Not sure yet'], visible: a => a.backend === 'Yes' },
  { id: 'databaseDetails', prompt: 'Which database are you using, and is it configured?', kind: 'text', required: true, visible: a => appCategories.includes(String(a.category)) && a.backend === 'Yes' && a.database === 'Yes' },
  { id: 'databaseHelp', prompt: 'Would you like help choosing a database?', kind: 'choice', options: ['Yes', 'No'], visible: a => appCategories.includes(String(a.category)) && a.backend === 'Yes' && a.database === 'No' },
  { id: 'deployment', prompt: 'Where should the project run?', kind: 'choice', options: ['Web / cloud', 'Mobile devices', 'Desktop computers', 'Not decided yet', 'Other'], visible: a => a.category !== undefined },
  { id: 'description', prompt: 'Anything else we should know?', help: 'Share goals, must-have features, or constraints. This is optional.', kind: 'long' },
];

export function visibleQuestions(answers: Answers) {
  return questions.filter(q => !q.visible || q.visible(answers));
}

export function pruneAnswers(answers: Answers): Answers {
  let current = { ...answers };
  for (let pass = 0; pass <= questions.length; pass += 1) {
    const visible = new Set(visibleQuestions(current).map(question => question.id));
    const next = Object.fromEntries(Object.entries(current).filter(([id]) => visible.has(id)));
    const unchanged = Object.keys(current).length === Object.keys(next).length
      && Object.keys(current).every(id => Object.prototype.hasOwnProperty.call(next, id));
    if (unchanged) return next;
    current = next;
  }
  return current;
}

export function hasAnswer(value: Answer | undefined): boolean {
  if (Array.isArray(value)) return value.length > 0;
  return typeof value === 'string' && value.trim().length > 0;
}

export function hasOtherSelection(question: Question, answers: Answers): boolean {
  if (!question.options?.includes('Other')) return false;
  const value = answers[question.id];
  return Array.isArray(value) ? value.includes('Other') : value === 'Other';
}

export function pruneCustomAnswers(answers: Answers, customAnswers: CustomAnswers): CustomAnswers {
  const normalizedAnswers = pruneAnswers(answers);
  const visible = new Set(visibleQuestions(normalizedAnswers).map(question => question.id));
  return Object.fromEntries(Object.entries(customAnswers).filter(([id]) => {
    const question = questions.find(item => item.id === id);
    return !!question && visible.has(id) && hasOtherSelection(question, normalizedAnswers);
  }));
}

export function requirementsFrom(answers: Answers, name: string, customAnswers: CustomAnswers = {}): CollectedRequirements {
  const normalized = pruneAnswers(answers);
  const normalizedCustom = pruneCustomAnswers(normalized, customAnswers);
  const applicable = visibleQuestions(normalized);
  const cleanAnswers = Object.fromEntries(applicable.filter(q => hasAnswer(normalized[q.id])).map(q => {
    const value = normalized[q.id];
    return [q.id, Array.isArray(value) ? value : value.trim()];
  }));
  return {
    name: name.trim(),
    answers: cleanAnswers,
    customAnswers: Object.fromEntries(Object.entries(normalizedCustom).filter(([, value]) => hasAnswer(value)).map(([id, value]) => [id, value.trim()])),
    sections: [
      { title: 'Project overview', fields: ['category', 'webKind', 'platform', 'mobileApproach'] },
      { title: 'Technology and data', fields: ['frontend', 'language', 'problem', 'model', 'modelDetails', 'dataset', 'datasetDetails'] },
      { title: 'Backend and access', fields: ['backend', 'auth', 'authMethods', 'database', 'databaseDetails', 'databaseHelp'] },
      { title: 'Deployment and notes', fields: ['deployment', 'description'] },
    ].map(section => ({ ...section, items: [
      ...section.fields.filter(id => applicable.some(q => q.id === id) && hasAnswer(normalized[id])).map(id => ({ id, question: questions.find(q => q.id === id)!.prompt, answer: Array.isArray(normalized[id]) ? normalized[id] : normalized[id].trim() })),
      ...section.fields.filter(id => hasAnswer(normalizedCustom[id])).map(id => ({ id: `${id}:other`, question: `Other answer for ${questions.find(q => q.id === id)!.prompt}`, answer: normalizedCustom[id].trim() })),
    ] })),
  };
}
