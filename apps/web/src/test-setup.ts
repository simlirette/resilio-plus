import '@testing-library/jest-dom'
import { vi } from 'vitest'

// Mock Next.js navigation — pages under test don't need a real router
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => '/',
}))
