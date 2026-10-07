import '@testing-library/jest-dom';
process.env.NEXT_PUBLIC_USE_MOCKS = 'true';
class RO { observe() {} unobserve() {} disconnect() {} }
(globalThis as unknown as { ResizeObserver: unknown }).ResizeObserver = RO;
