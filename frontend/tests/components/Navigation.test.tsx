import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AppLayout } from '@/layouts/AppLayout';
import { AuthProvider } from '@/context/AuthContext';
import { ThemeProvider } from '@/context/ThemeContext';
jest.mock('next/router', () => ({ useRouter: () => ({ pathname: '/dashboard', push: jest.fn(), replace: jest.fn() }) }));
const setup = () => render(<ThemeProvider><AuthProvider><AppLayout><p>content</p></AppLayout></AuthProvider></ThemeProvider>);
beforeEach(() => { localStorage.setItem('token', 't'); localStorage.setItem('user', JSON.stringify({ name: 'Tester', email: 't@x.com' })); });
afterEach(() => { localStorage.clear(); document.documentElement.classList.remove('dark'); });
describe('navigation', () => {
  it('renders all nav items and marks the active page', async () => {
    setup();
    for (const n of ['Token Trim', 'Dashboard', 'Projects', 'API Key', 'Team', 'Profile', 'Settings', 'LLM Plans', 'Guide', 'About'])
      expect(await screen.findByRole('link', { name: n })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Dashboard' })).toHaveAttribute('aria-current', 'page');
  });
  it('shows recent activity and project history in the sidebar', async () => {
    setup();
    expect(await screen.findByText('Recent activity')).toBeInTheDocument();
    expect(screen.getByText('Project history')).toBeInTheDocument();
    expect(await screen.findByText('Summarize quarterly report', {}, { timeout: 3000 })).toBeInTheDocument();
  });
  it('collapses and expands the sidebar', async () => {
    const user = userEvent.setup(); setup();
    const btn = await screen.findByRole('button', { name: 'Toggle sidebar' });
    expect(btn).toHaveAttribute('aria-expanded', 'true');
    await user.click(btn); expect(btn).toHaveAttribute('aria-expanded', 'false');
    expect(localStorage.getItem('sidebarCollapsed')).toBe('1');
  });
  it('opens the mobile menu', async () => {
    const user = userEvent.setup(); setup();
    await user.click(await screen.findByRole('button', { name: 'Menu' }));
    expect(screen.getAllByRole('link', { name: 'Dashboard' })).toHaveLength(2);
  });
  it('toggles and persists the theme', async () => {
    const user = userEvent.setup(); setup();
    await user.click(await screen.findByRole('button', { name: 'Switch to dark mode' }));
    expect(document.documentElement).toHaveClass('dark');
    expect(localStorage.getItem('theme')).toBe('dark');
    expect(screen.getByRole('button', { name: 'Switch to light mode' })).toBeInTheDocument();
  });
});
