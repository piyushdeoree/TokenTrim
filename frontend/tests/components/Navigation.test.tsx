import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AppLayout } from '@/layouts/AppLayout';
import { AuthProvider } from '@/context/AuthContext';
import { ThemeProvider } from '@/context/ThemeContext';
jest.mock('next/router', () => ({ useRouter: () => ({ pathname: '/dashboard', push: jest.fn(), replace: jest.fn() }) }));
const mockUseActivity = jest.fn();
jest.mock('@/hooks/useActivity', () => ({ useActivity: () => mockUseActivity() }));
const setup = () => render(<ThemeProvider><AuthProvider><AppLayout><p>content</p></AppLayout></AuthProvider></ThemeProvider>);
beforeEach(() => {
  localStorage.setItem('token', 't'); localStorage.setItem('user', JSON.stringify({ name: 'Tester', email: 't@x.com' }));
  mockUseActivity.mockReturnValue({ state: { status: 'success', data: [{ id: 1, title: 'Summarize quarterly report', project: 'Project history', saved: 12, date: '2026-11-16T10:00:00Z' }] }, reload: jest.fn(), setState: jest.fn() });
});
afterEach(() => { localStorage.clear(); document.documentElement.classList.remove('dark'); jest.clearAllMocks(); });
describe('navigation', () => {
  it('renders all nav items and marks the active page', async () => {
    setup();
    for (const n of ['Token Trim', 'Dashboard', 'Projects', 'API Key', 'Team', 'Profile', 'Settings', 'LLM Plans', 'Guide', 'About'])
      expect(await screen.findByRole('link', { name: n })).toBeInTheDocument();
    const nav = screen.getByRole('navigation', { name: 'Main' });
    expect(within(nav).queryByRole('link', { name: 'Prompt History' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /View Recent History/ })).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByRole('link', { name: 'View full prompt history' })).toHaveAttribute('href', '/history');
    expect(screen.getByRole('link', { name: 'Dashboard' })).toHaveAttribute('aria-current', 'page');
  });
  it('shows recent history from the existing history data', async () => {
    setup();
    expect(screen.getByText('View Recent History')).toBeInTheDocument();
    expect(screen.getByText(/Project history/)).toBeInTheDocument();
    expect(screen.getByText('Summarize quarterly report')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Prompt History' })).not.toBeInTheDocument();
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
    const menus = screen.getAllByRole('navigation', { name: 'Main' });
    const mobileMenu = menus[menus.length - 1];
    expect(within(mobileMenu).getByRole('link', { name: 'Dashboard' })).toBeInTheDocument();
    expect(within(mobileMenu).queryByRole('link', { name: 'Prompt History' })).not.toBeInTheDocument();
  });
  it('toggles and persists the theme', async () => {
    const user = userEvent.setup(); setup();
    await user.click(await screen.findByRole('button', { name: 'Switch to dark mode' }));
    expect(document.documentElement).toHaveClass('dark');
    expect(localStorage.getItem('theme')).toBe('dark');
    expect(screen.getByRole('button', { name: 'Switch to light mode' })).toBeInTheDocument();
  });
});
