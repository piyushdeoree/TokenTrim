export const MAX_PROMPT_CHARS = 20000;
export function validateAnalyzeForm(prompt: string, model: string) {
  const errors: { prompt?: string; model?: string } = {};
  if (!prompt.trim()) errors.prompt = 'Enter a prompt to analyze.';
  else if (prompt.length > MAX_PROMPT_CHARS) errors.prompt = `Prompt is over ${MAX_PROMPT_CHARS.toLocaleString()} characters. Shorten it and try again.`;
  if (!model) errors.model = 'Select a model.';
  return errors;
}
