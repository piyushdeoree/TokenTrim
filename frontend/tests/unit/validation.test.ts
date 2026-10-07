import { validateAnalyzeForm, MAX_PROMPT_CHARS } from '@/utils/validation';
describe('validateAnalyzeForm', () => {
  it('requires prompt and model', () => expect(validateAnalyzeForm('  ', '')).toEqual({ prompt: 'Enter a prompt to analyze.', model: 'Select a model.' }));
  it('accepts valid input', () => expect(validateAnalyzeForm('hello', 'gpt-4o')).toEqual({}));
  it('rejects overlong prompts', () => expect(validateAnalyzeForm('a'.repeat(MAX_PROMPT_CHARS + 1), 'gpt-4o').prompt).toMatch(/over/));
});
