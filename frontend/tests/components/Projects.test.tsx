import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Projects from '@/pages/projects';
describe('projects', () => {
  it('lists projects', async () => { render(<Projects />); expect(await screen.findByText('Support bot')).toBeInTheDocument(); });
  it('validates and creates a project', async () => {
    const user = userEvent.setup(); render(<Projects />);
    await user.click(await screen.findByRole('button', { name: 'Create project' }));
    await user.click(screen.getAllByRole('button', { name: 'Create project' })[1]);
    expect(screen.getByText('Project name must be at least 2 characters.')).toBeInTheDocument();
    await user.type(screen.getByLabelText('Project name'), 'New project');
    await user.click(screen.getAllByRole('button', { name: 'Create project' })[1]);
    await screen.findByText('Support bot');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
