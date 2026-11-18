import { render, screen } from '@testing-library/react';
import { ExecutionHistoryPreview } from '@/components/execution/ExecutionHistoryPreview';

it('shows a clearly labeled demo execution history with status, usage, duration, and cost', () => {
  render(<ExecutionHistoryPreview showDemo />);
  expect(screen.getByText('Demo sample data')).toBeInTheDocument();
  expect(screen.getByText('OpenAI · GPT-4o mini')).toBeInTheDocument();
  expect(screen.getAllByText('Succeeded')).toHaveLength(2);
  expect(screen.getAllByText('Input tokens')).toHaveLength(3);
  expect(screen.getAllByText('Output tokens')).toHaveLength(3);
  expect(screen.getAllByText('Execution duration')).toHaveLength(3);
  expect(screen.getAllByText('Actual execution cost')).toHaveLength(3);
  expect(screen.getByText(/USD\s*0\.000081/)).toBeInTheDocument();
  expect(screen.getAllByText('Not available').length).toBeGreaterThanOrEqual(4);
  expect(screen.getByText(/not saved runs or real provider usage/)).toBeInTheDocument();
});

it('does not present sample records when demo mode is disabled', () => {
  render(<ExecutionHistoryPreview showDemo={false} />);
  expect(screen.getByText('Execution history will appear here when available.')).toBeInTheDocument();
  expect(screen.queryByText('OpenAI · GPT-4o mini')).not.toBeInTheDocument();
});
