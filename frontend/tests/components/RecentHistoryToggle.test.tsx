import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RecentHistoryToggle } from '@/components/navigation/RecentHistoryToggle';

const mockUseActivity = jest.fn();
jest.mock('@/hooks/useActivity', () => ({ useActivity: () => mockUseActivity() }));

const reload = jest.fn();
const setActivity = (state: unknown) => mockUseActivity.mockReturnValue({ state, reload, setState: jest.fn() });

beforeEach(() => { localStorage.clear(); setActivity({ status: 'success', data: [] }); });
afterEach(() => { localStorage.clear(); jest.clearAllMocks(); });

describe('RecentHistoryToggle', () => {
  it('expands and collapses without navigation, persists state, and links to full history', async () => {
    const user = userEvent.setup();
    const { unmount } = render(<RecentHistoryToggle />);
    const toggle = await screen.findByRole('button', { name: /View Recent History/ });
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    const list = document.querySelector('[id^="recent-history-list-"]');
    expect(list).toHaveClass('overflow-y-auto', 'overscroll-contain');
    expect(list).toHaveClass('max-h-[30vh]', 'lg:max-h-[38vh]');
    expect(screen.getByRole('link', { name: 'View full prompt history' })).toHaveAttribute('href', '/history');

    await user.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(localStorage.getItem('recentHistoryExpanded')).toBe('0');
    expect(screen.queryByText('Nothing here yet.')).not.toBeInTheDocument();
    unmount();

    render(<RecentHistoryToggle />);
    expect(await screen.findByRole('button', { name: /View Recent History/ })).toHaveAttribute('aria-expanded', 'false');
  });

  it('shows the loading, empty, and error states with retry', async () => {
    setActivity({ status: 'loading' });
    const { rerender } = render(<RecentHistoryToggle />);
    expect(await screen.findByText('Loading history...')).toBeInTheDocument();

    setActivity({ status: 'success', data: [] });
    rerender(<RecentHistoryToggle />);
    expect(await screen.findByText('Nothing here yet.')).toBeInTheDocument();

    setActivity({ status: 'error', message: 'network error' });
    rerender(<RecentHistoryToggle />);
    expect(await screen.findByText(/Unable to load history/)).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Retry' }));
    expect(reload).toHaveBeenCalledTimes(1);
  });
});
