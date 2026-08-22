import { vi, beforeEach } from 'vitest'

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

const storage = {
  store: {},
  getItem(key) {
    return this.store[key] ?? null
  },
  setItem(key, value) {
    this.store[key] = String(value)
  },
  removeItem(key) {
    delete this.store[key]
  },
  clear() {
    this.store = {}
  },
}

Object.defineProperty(window, 'localStorage', {
  value: storage,
  writable: true,
  configurable: true,
})

globalThis.localStorage = storage

beforeEach(() => {
  window.localStorage.clear()
})
