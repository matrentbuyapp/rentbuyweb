import "@testing-library/jest-dom/vitest";

// Mock localStorage
const store: Record<string, string> = {};
Object.defineProperty(window, "localStorage", {
  value: {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, val: string) => { store[key] = val; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { Object.keys(store).forEach((k) => delete store[k]); },
  },
});

// Mock crypto.randomUUID
Object.defineProperty(window, "crypto", {
  value: {
    randomUUID: () => "test-uuid-1234",
  },
});

// Mock IntersectionObserver
class MockIntersectionObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
Object.defineProperty(window, "IntersectionObserver", {
  value: MockIntersectionObserver,
});

// Mock scrollIntoView
Element.prototype.scrollIntoView = () => {};

// Mock fetch globally (individual tests can override)
global.fetch = vi.fn(() =>
  Promise.resolve({
    ok: false,
    status: 404,
    text: () => Promise.resolve("not found"),
    json: () => Promise.resolve({}),
  } as Response)
);

// Suppress ResizeObserver errors from Recharts
class MockResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
Object.defineProperty(window, "ResizeObserver", {
  value: MockResizeObserver,
});
