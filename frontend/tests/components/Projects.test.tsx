import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Projects from '@/pages/projects';
import { load, send } from '@/services/data';

jest.mock('@/services/data', () => ({
  load: jest.fn().mockResolvedValue([{ id: 7, name: 'Support bot', description: null, owner_id: 1, team_id: null, created_at: '2025-01-01', updated_at: '2025-01-01' }]),
  send: jest.fn().mockResolvedValue({ id: 42, name: 'New project' }),
}));

describe('projects', () => {
  beforeEach(() => { localStorage.clear(); jest.clearAllMocks(); });

  it('lists projects', async () => {
    render(<Projects />);
    expect(await screen.findByText('Support bot')).toBeInTheDocument();
  });

  it('guides project creation through tailored questions and review', async () => {
    const user = userEvent.setup();
    render(<Projects />);
    await user.click(await screen.findByRole('button', { name: 'Create project' }));
    const dialog = screen.getByRole('dialog', { name: 'Create a project' });
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }));
    expect(await within(dialog).findByText('Project name must be at least 2 characters.')).toBeInTheDocument();
    await user.type(within(dialog).getByLabelText('Project name'), 'New project');
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }));
    await user.click(within(dialog).getByRole('button', { name: 'Web Application' }));
    expect(await within(dialog).findByText('What kind of web application is it?')).toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: 'Dashboard' }));
    expect(await within(dialog).findByText('Which frontend technology would you prefer?')).toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: 'Next.js' }));
    expect(await within(dialog).findByText('Will your project need a backend?')).toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: /^Yes$/ }));
    expect(await within(dialog).findByText('Will users need to sign in?')).toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: /^Yes$/ }));
    expect(await within(dialog).findByText('Which sign-in methods do you need?')).toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: 'Email and password' }));
    await user.click(within(dialog).getByRole('button', { name: 'Other' }));
    const authOther = within(dialog).getByLabelText('Your answer for Other');
    await user.type(authOther, 'Passkey');
    await user.click(within(dialog).getByRole('button', { name: 'Other' }));
    expect(within(dialog).queryByLabelText('Your answer for Other')).not.toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: 'Other' }));
    expect(within(dialog).getByLabelText('Your answer for Other')).toHaveValue('');
    await user.type(within(dialog).getByLabelText('Your answer for Other'), 'Passkey');
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }));
    expect(await within(dialog).findByText('Do you already have a database?')).toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: 'Previous' }));
    expect(within(dialog).getByLabelText('Your answer for Other')).toHaveValue('Passkey');
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }));
    await user.click(within(dialog).getByRole('button', { name: 'Previous' }));
    await user.click(within(dialog).getByRole('button', { name: 'Previous' }));
    await user.click(within(dialog).getByRole('button', { name: 'Previous' }));
    await user.click(within(dialog).getByRole('button', { name: /^No$/ }));
    expect(await within(dialog).findByText('Where should the project run?')).toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: 'Web / cloud' }));
    expect(await within(dialog).findByRole('heading', { name: 'Anything else we should know?' })).toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: 'Skip' }));
    expect(await within(dialog).findByText('Review your project requirements')).toBeInTheDocument();
    expect(within(dialog).getByText('Next.js')).toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: 'Submit requirements' }));
    expect(send).toHaveBeenCalledWith('post', '/projects', { name: 'New project' });
    expect(JSON.parse(localStorage.getItem('tokentrim:project-requirements:42') ?? '{}').answers).toMatchObject({
      category: 'Web Application', webKind: 'Dashboard', frontend: 'Next.js', backend: 'No', deployment: 'Web / cloud',
    });
    expect(JSON.parse(localStorage.getItem('tokentrim:project-requirements:42') ?? '{}').answers).not.toHaveProperty('auth');
    expect(JSON.parse(localStorage.getItem('tokentrim:project-requirements:42') ?? '{}').answers).not.toHaveProperty('authMethods');
    expect(JSON.parse(localStorage.getItem('tokentrim:project-requirements:42') ?? '{}').customAnswers).not.toHaveProperty('authMethods');
  });

  it('supports mobile multi-select, custom follow-ups, and editing from review', async () => {
    const user = userEvent.setup();
    render(<Projects />);
    await user.click(await screen.findByRole('button', { name: 'Create project' }));
    const dialog = screen.getByRole('dialog', { name: 'Create a project' });
    await user.type(within(dialog).getByLabelText('Project name'), 'Mobile client');
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }));
    await user.click(within(dialog).getByRole('button', { name: 'Mobile Application' }));
    await user.click(within(dialog).getByRole('button', { name: 'Android' }));
    await user.click(within(dialog).getByRole('button', { name: 'iOS' }));
    await user.click(within(dialog).getByRole('button', { name: 'Android' }));
    expect(within(dialog).getByRole('button', { name: 'Android' })).toHaveAttribute('aria-pressed', 'false');
    await user.click(within(dialog).getByRole('button', { name: 'Android' }));
    expect(within(dialog).getByRole('button', { name: 'iOS' })).toHaveAttribute('aria-pressed', 'true');
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }));
    await user.click(within(dialog).getByRole('button', { name: 'Other' }));
    const approach = within(dialog).getByLabelText('Your answer for Other');
    await user.type(approach, 'Kotlin Multiplatform');
    await user.click(within(dialog).getByRole('button', { name: 'Native' }));
    expect(within(dialog).queryByLabelText('Your answer for Other')).not.toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: 'Previous' }));
    await user.click(within(dialog).getByRole('button', { name: 'Other' }));
    expect(within(dialog).getByLabelText('Your answer for Other')).toHaveValue('');
    await user.type(within(dialog).getByLabelText('Your answer for Other'), 'Kotlin Multiplatform');
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }));
    await user.click(within(dialog).getByRole('button', { name: 'Previous' }));
    expect(within(dialog).getByLabelText('Your answer for Other')).toHaveValue('Kotlin Multiplatform');
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }));
    await user.click(within(dialog).getByRole('button', { name: 'Other' }));
    await user.type(within(dialog).getByLabelText('Your answer for Other'), 'Compose Multiplatform');
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }));
    await user.click(within(dialog).getByRole('button', { name: /^No$/ }));
    await user.click(within(dialog).getByRole('button', { name: 'Mobile devices' }));
    await user.type(within(dialog).getByLabelText('Anything else we should know?'), 'First draft');
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }));
    expect(await within(dialog).findByText('Review your project requirements')).toBeInTheDocument();
    expect(within(dialog).getByText(/Android.*iOS|iOS.*Android/)).toBeInTheDocument();
    expect(within(dialog).getByText('Kotlin Multiplatform')).toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: 'Edit Anything else we should know?' }));
    const notes = within(dialog).getByLabelText('Anything else we should know?');
    await user.clear(notes);
    await user.type(notes, 'Updated after review');
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }));
    expect(await within(dialog).findByText('Review your project requirements')).toBeInTheDocument();
    expect(within(dialog).getByText('Updated after review')).toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: 'Submit requirements' }));
    const submitted = JSON.parse(localStorage.getItem('tokentrim:project-requirements:42') ?? '{}').answers;
    expect(submitted).toMatchObject({
      category: 'Mobile Application', platform: ['iOS', 'Android'], mobileApproach: 'Other',
      frontend: 'Other', description: 'Updated after review',
    });
    expect(JSON.parse(localStorage.getItem('tokentrim:project-requirements:42') ?? '{}').customAnswers).toMatchObject({
      mobileApproach: 'Kotlin Multiplatform', frontend: 'Compose Multiplatform',
    });
  });

  it('rejects whitespace-only required text and restores a saved draft', async () => {
    const user = userEvent.setup();
    const first = render(<Projects />);
    await user.click(await screen.findByRole('button', { name: 'Create project' }));
    const dialog = screen.getByRole('dialog', { name: 'Create a project' });
    await user.type(within(dialog).getByLabelText('Project name'), 'AI prototype');
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }));
    await user.click(within(dialog).getByRole('button', { name: 'AI / Machine Learning' }));
    const problem = within(dialog).getByLabelText('What problem should your AI or data project solve?');
    for (const invalid of ['', '   ', '\t', '\n\r']) {
      fireEvent.change(problem, { target: { value: invalid } });
      await user.click(within(dialog).getByRole('button', { name: 'Continue' }));
      expect(await within(dialog).findByRole('alert')).toHaveTextContent('Please provide an answer');
    }
    await user.clear(problem);
    await user.type(problem, 'Classify support requests');
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }));
    expect(await within(dialog).findByText('Do you have a model or algorithm in mind?')).toBeInTheDocument();
    first.unmount();

    render(<Projects />);
    await user.click(await screen.findByRole('button', { name: 'Create project' }));
    const restored = screen.getByRole('dialog', { name: 'Create a project' });
    expect(await within(restored).findByText('Do you have a model or algorithm in mind?')).toBeInTheDocument();
    expect(JSON.parse(localStorage.getItem('tokentrim:project-questionnaire:draft') ?? '{}')).toMatchObject({
      name: 'AI prototype', answers: { category: 'AI / Machine Learning', problem: 'Classify support requests' },
    });
    await user.click(within(restored).getByRole('button', { name: 'Cancel' }));
  });

  it('reviews and saves Other text selected with other multi-choice options', async () => {
    const user = userEvent.setup();
    render(<Projects />);
    await user.click(await screen.findByRole('button', { name: 'Create project' }));
    const dialog = screen.getByRole('dialog', { name: 'Create a project' });
    await user.type(within(dialog).getByLabelText('Project name'), 'Auth choices');
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }));
    await user.click(within(dialog).getByRole('button', { name: 'Web Application' }));
    await user.click(within(dialog).getByRole('button', { name: 'Dashboard' }));
    await user.click(within(dialog).getByRole('button', { name: 'Next.js' }));
    await user.click(within(dialog).getByRole('button', { name: /^Yes$/ }));
    await user.click(within(dialog).getByRole('button', { name: /^Yes$/ }));
    await user.click(within(dialog).getByRole('button', { name: 'Email and password' }));
    await user.click(within(dialog).getByRole('button', { name: 'Other' }));
    await user.type(within(dialog).getByLabelText('Your answer for Other'), 'Passkey');
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }));
    await user.click(within(dialog).getByRole('button', { name: 'Skip' }));
    await user.click(within(dialog).getByRole('button', { name: 'Web / cloud' }));
    await user.click(within(dialog).getByRole('button', { name: 'Skip' }));
    expect(await within(dialog).findByText('Review your project requirements')).toBeInTheDocument();
    expect(within(dialog).getByText('Passkey')).toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: 'Submit requirements' }));
    const result = JSON.parse(localStorage.getItem('tokentrim:project-requirements:42') ?? '{}');
    expect(result.answers.authMethods).toEqual(['Email and password', 'Other']);
    expect(result.customAnswers.authMethods).toBe('Passkey');
  });
});
