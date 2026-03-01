/**
 * Jest Setup File
 * ---------------
 * Setup and configuration for Jest tests.
 */

require('@testing-library/jest-dom');

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock IntersectionObserver
class IntersectionObserverMock {
  constructor(callback) {
    this.callback = callback;
  }
  observe() { return null; }
  unobserve() { return null; }
  disconnect() { return null; }
}

Object.defineProperty(window, 'IntersectionObserver', {
  writable: true,
  value: IntersectionObserverMock,
});

// Suppress console warnings during tests
const originalWarn = console.warn;
console.warn = (...args) => {
  // Filter out specific warnings if needed
  if (typeof args[0] === 'string' && args[0].includes?.('React')) return;
  originalWarn(...args);
};
